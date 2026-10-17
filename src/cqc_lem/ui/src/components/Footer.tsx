import { Link } from 'react-router-dom'
import { useAppInfo } from '../hooks/useAppInfo'
import LegalDisclaimer from './marketing/LegalDisclaimer'

export default function Footer() {
  const { data } = useAppInfo()
  const year = new Date().getFullYear()

  return (
    <footer className="border-t border-hairline bg-raised">
      <div className="box-content max-w-6xl mx-auto px-4 pt-4 flex flex-col sm:flex-row items-center justify-center gap-2 sm:gap-4 text-fg-muted">
        <span className="text-xs">© {year} Christopher Queen Consulting. All rights reserved.</span>
        <div className="flex items-center gap-3 text-xs">
          <Link to="/privacy-policy" className="hover:text-fg transition-colors">
            Privacy Policy
          </Link>
          <span aria-hidden="true" className="text-fg-muted">|</span>
          <Link to="/terms-and-conditions" className="hover:text-fg transition-colors">
            Terms and Conditions
          </Link>
        </div>
        {data?.show_version && data.version && (
          <span className="text-xs leading-none text-fg-muted">v{data.version}</span>
        )}
      </div>
      {/* Same notice the marketing footer carries (issue #1300). One surface stating it and the
          others not would read as decoration rather than a statement — and the legal pages, where
          someone actually looks for it, render inside this chrome. */}
      <div className="box-content max-w-6xl mx-auto px-4 pb-4 pt-2 text-center text-fg-muted">
        <LegalDisclaimer className="max-w-measure mx-auto" />
      </div>
    </footer>
  )
}
