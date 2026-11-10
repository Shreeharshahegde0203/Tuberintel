"""Public HTML price-table connector. No API keys, CAPTCHA bypass or fixed prices."""
from datetime import date, datetime, timezone
from html.parser import HTMLParser
import re
import time
from threading import RLock
_lock = RLock()

URL = 'https://acrop.app/mandi/karnataka/bengaluru-rural/bangalore/potato'
SOURCE = 'Public webpage: ACROP | ' + URL
MARKET = 'Bangalore APMC (published aggregate)'
VARIETY = 'Published aggregate'
TTL_SECONDS = 3600
_status = {}

class WebPriceError(RuntimeError):
    pass

class TableReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[]; self.cells=[]; self.cell=[]; self.inside=False
    def handle_starttag(self, tag, attrs):
        if tag=='tr': self.cells=[]
        if tag in ('td','th'): self.inside=True; self.cell=[]
    def handle_data(self,data):
        if self.inside: self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.inside:
            self.inside=False; self.cells.append(' '.join(''.join(self.cell).split()))
        if tag=='tr' and self.cells: self.rows.append(self.cells)

def parse_prices(html, today=None):
    today=today or date.today()
    reader=TableReader(); reader.feed(html)
    output={}
    headers_seen=False
    def money(value):
        currency = chr(0x20B9)
        match = re.search(
            re.escape(currency) + r"\s*([\d,]+(?:\.\d+)?)",
            value,
        )
        if not match:
            raise ValueError("Missing or invalid rupee price")
        return float(match.group(1).replace(",", ""))
    for row in reader.rows:
        if len(row)>=4 and row[0].strip().lower()=='date':
            headers_seen=(['modal price','minimum price','maximum price']==[s.strip().lower() for s in row[1:4]])
            continue
        if not headers_seen or len(row)<4: continue
        try:
            day=datetime.strptime(row[0],'%d %b %Y').date()
            # Modal column must explicitly identify quintal units.
            if 'quintal' not in row[1].lower(): raise ValueError('Unknown price units')
            modal,minimum,maximum=map(money,row[1:4])
        except ValueError: continue
        if day>today or not 0<minimum<=modal<=maximum: continue
        record=dict(state='Karnataka',district='Bengaluru',market=MARKET,commodity='Potato',variety=VARIETY,
            grade='Published aggregate',arrival_date=day,min_price=minimum,max_price=maximum,
            modal_price=modal,source=SOURCE)
        if day in output and output[day]!=record:
            raise WebPriceError('Conflicting observations for one reporting date')
        output[day]=record
    if not output:
        raise WebPriceError('No valid daily price rows found. Page layout/units may have changed; no prices imported.')
    return [output[d] for d in sorted(output)]

def fetch_prices():
    import httpx
    try:
        response=httpx.get(URL,timeout=httpx.Timeout(25,connect=10),follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise WebPriceError(f'Public price webpage unavailable ({type(exc).__name__}); existing observations retained.') from exc
    return parse_prices(response.text)

def _sync(db, state='Karnataka', district=None, force=True):
    from sqlalchemy import select
    from app.models import MarketPrice
    if state not in (None,'Karnataka') or district not in (None,'','Bengaluru','Bangalore'):
        return dict(source=SOURCE,live_data=False,received=0,inserted=0,updated=0,
            note='This connector currently covers Bangalore APMC aggregate prices only. No other location is substituted.')
    if not force and time.monotonic()-_status.get('last_attempt',-1e10)<TTL_SECONDS:
        return dict(_status.get('result',{}))
    _status['last_attempt']=time.monotonic()
    try:
        records=fetch_prices()
        inserted=updated=0
        now=datetime.now(timezone.utc)
        for record in records:
            keys=('state','district','market','commodity','variety','grade','arrival_date')
            existing=db.scalar(select(MarketPrice).where(*[getattr(MarketPrice,k)==record[k] for k in keys]))
            if existing is None:
                existing=MarketPrice(**record);db.add(existing);inserted+=1
            else:
                changed=any(getattr(existing,k)!=record[k] for k in ('min_price','max_price','modal_price','source'))
                for k in ('min_price','max_price','modal_price','source'): setattr(existing,k,record[k])
                updated+=int(changed)
            if hasattr(existing,'fetched_at'): existing.fetched_at=now
        from app.services.market_service import MarketService
        service = MarketService()
        locations = {
            (record['state'], record['district'], record['market'])
            for record in records
        }
        for state_name, district_name, market_name in sorted(locations):
            service._upsert_mandi(
                db, state=state_name, district=district_name,
                market=market_name, source=SOURCE,
            )
            db.flush()
        db.commit()
        last=max(r['arrival_date'] for r in records)
        result=dict(source=SOURCE,source_url=URL,live_data=True,received=len(records),inserted=inserted,updated=updated,
            latest_date=last.isoformat(),fetched_at=now.isoformat(),fallback_used=False,
            note=f'Fetched public HTML price history; last reporting date {last}. This is a third-party aggregate, not a direct government API. Missing days are not invented.')
        _status.update(result=result,error=None)
        return result
    except Exception as exc:
        db.rollback()
        _status['error']=str(exc)[:500]
        _status['result']=dict(source=SOURCE,live_data=False,received=0,inserted=0,updated=0,note=_status['error'])
        if force: raise
        return dict(_status['result'])

def sync(db, state='Karnataka', district=None, force=True):
    with _lock:
        return _sync(db,state=state,district=district,force=force)

def ensure_web_prices(db,state='Karnataka'):
    return sync(db,state=state,force=False)

def web_status():
    return dict(_status.get('result',{}),error=_status.get('error'),source_url=URL,
        coverage='Bangalore APMC aggregate only',refresh_interval_seconds=TTL_SECONDS)

if __name__ == '__main__':
    # Direct standalone probe: downloads HTML and prints observations; no DB imports/writes.
    import json
    try:
        records=fetch_prices()
        print(json.dumps(dict(source=SOURCE,count=len(records),first_date=str(records[0]['arrival_date']),
            latest_date=str(records[-1]['arrival_date']),latest_modal=records[-1]['modal_price']),indent=2))
    except WebPriceError as exc:
        raise SystemExit(str(exc))
