import type { ReactNode } from 'react'
import { Component } from 'react'
import { AlertTriangle } from 'lucide-react'

type Props = {
  children: ReactNode
  title?: string
}

type State = {
  hasError: boolean
  message: string
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = {
    hasError: false,
    message: '',
  }

  static getDerivedStateFromError(error: Error): State {
    return {
      hasError: true,
      message: error.message,
    }
  }

  componentDidCatch(error: Error) {
    console.error('route_error_boundary', error)
  }

  reset = () => {
    this.setState({ hasError: false, message: '' })
  }

  render() {
    if (this.state.hasError) {
      const message = humanizeError(this.state.message)
      return (
        <div className="state-panel state-error">
          <AlertTriangle size={28} />
          <strong>{this.props.title || 'This page could not be loaded'}</strong>
          <p>{message || 'An unexpected error interrupted the page render.'}</p>
          <button className="button button-secondary" type="button" onClick={this.reset}>
            Try again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

function humanizeError(message: string) {
  if (/network ?error/i.test(message) || /failed to fetch/i.test(message)) {
    return 'The backend API is not reachable. Start the backend server and confirm the frontend API URL is correct.'
  }
  return message
}
