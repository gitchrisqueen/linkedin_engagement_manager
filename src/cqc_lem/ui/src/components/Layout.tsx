import { Suspense } from 'react'
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/useAuth'
import AccountReadinessBanner from './AccountReadinessBanner'
import FeedbackWidget from './FeedbackWidget'
import FloatingDock from './FloatingDock'
import Footer from './Footer'
import PostHogSurveyModal from './PostHogSurveyModal'
import ShippedNotice from './ShippedNotice'
import StrongFactorGate from './StrongFactorGate'
import StrongFactorPrompt from './StrongFactorPrompt'
import SurveyModal from './SurveyModal'

// Pages whose features depend on a fully set-up account — show the readiness banner here.
const AUTOMATION_PATHS = ['/content', '/schedule', '/review', '/avatars']

const navLinks = [
  { to: '/', label: 'Home', end: true },
  { to: '/account', label: 'Account' },
  { to: '/avatars', label: 'Avatars' },
  { to: '/content', label: 'Content' },
]

// One link style for every nav item: a full-height row with a 2px primary bar under the active
// page (the marketing nav's hairline chrome, carried into the app).
function navLinkClass({ isActive }: { isActive: boolean }): string {
  return `inline-flex h-16 items-center border-b-2 text-sm whitespace-nowrap transition-colors ${
    isActive
      ? 'border-accent font-semibold text-fg'
      : 'border-transparent font-medium text-fg-muted hover:text-fg'
  }`
}

const adminNavLinks = [
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/feedback', label: 'Feedback Triage' },
  { to: '/admin/audit-log', label: 'Audit Log' },
]

export default function Layout() {
  const { user, logout, openLoginModal, isAdmin, enrollmentRequired } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const showReadiness = !!user && AUTOMATION_PATHS.some((p) => location.pathname.startsWith(p))

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  return (
    <div className="lem-app min-h-screen flex flex-col bg-page">
      <nav className="bg-raised border-b border-hairline sticky top-0 z-10">
        <div className="box-content max-w-6xl mx-auto px-4 flex items-center gap-4 sm:gap-8 h-16">
          {/* -ml-[5px]: the artwork has 50 of 1340 px transparent on its left, about 5px here, so
              the visible mark starts on the page's left edge (same as the marketing nav). */}
          <NavLink to="/" className="shrink-0" aria-label="LinkedIn Engagement Manager, home">
            <img
              src="/brand/lem-wordmark.png"
              alt=""
              width={1340}
              height={300}
              className="-ml-[5px] h-7 w-auto"
            />
          </NavLink>
          {/* On a phone the links no longer push the account controls off the right edge: this row
              is the only thing allowed to shrink, and it scrolls sideways instead (issue #894). */}
          {user && (
            <div
              data-testid="nav-links"
              className="flex items-center gap-5 sm:gap-7 min-w-0 overflow-x-auto scrollbar-none [mask-image:linear-gradient(to_right,#000_85%,transparent)] sm:[mask-image:none]"
            >
              {navLinks.map(({ to, label, end }) => (
                <NavLink key={to} to={to} end={end} className={navLinkClass}>
                  {label}
                </NavLink>
              ))}
              {isAdmin && adminNavLinks.map(({ to, label }) => (
                <NavLink key={to} to={to} className={navLinkClass}>
                  {label}
                </NavLink>
              ))}
            </div>
          )}
          <div className="ml-auto flex items-center gap-3 shrink-0">
            {user ? (
              <>
                <span className="text-sm text-fg-muted hidden sm:inline">
                  Logged in as: <span className="font-medium text-fg">{user.email}</span>
                </span>
                <button
                  onClick={handleLogout}
                  className="min-h-11 px-2 text-sm font-medium text-fg-muted hover:text-fg transition-colors"
                >
                  Log out
                </button>
              </>
            ) : (
              <button
                onClick={openLoginModal}
                className="min-h-11 px-2 text-sm font-semibold text-accent hover:underline"
              >
                Login / Sign Up
              </button>
            )}
          </div>
        </div>
      </nav>
      <main className="flex-1 w-full max-w-[74rem] mx-auto px-4 py-8 sm:py-10">
        {/* Mandatory strong-factor enrolment (issue #905). The gate REPLACES the page: a held
            session is refused everywhere but the enrolment surface, so rendering the app behind it
            would only produce 403s. The prompt is the pre-deadline half. */}
        {enrollmentRequired ? (
          <StrongFactorGate />
        ) : (
          <>
            {showReadiness && <AccountReadinessBanner />}
            {user && <StrongFactorPrompt />}
            {/* "You asked, we shipped" + its micro-CSAT — renders only when a fix this user
                reported has shipped and they haven't acknowledged it yet (issue #502) */}
            {user && <ShippedNotice />}
            {/* The app's routes are lazy since issue #1300, and a lazy route with no boundary
                above it throws instead of suspending. This one sits INSIDE the chrome on purpose:
                a boundary further up would blank the nav and the footer for the frame a chunk
                takes to arrive. */}
            <Suspense fallback={<div className="h-40" aria-busy="true" />}>
              <Outlet />
            </Suspense>
          </>
        )}
      </main>
      <Footer />
      {/* Shared bottom-right stack — page-level floating controls (Settings' Save All) portal in
          here so nothing can be buried under the feedback launcher again (issue #596). */}
      <FloatingDock>
        <FeedbackWidget />
      </FloatingDock>
      {/* Survey modal — renders only when the server says a survey is due (issue #501). Both
          modals stand down while a session is held to enrolment: they poll endpoints outside that
          surface, and asking someone to rate us mid-lockout is the wrong moment anyway. */}
      {user && !enrollmentRequired && <SurveyModal />}
      {/* PostHog-targeted NPS/CSAT, drawn in LEM's own chrome (issue #653). Stands down whenever
          the bespoke modal above has something to ask, so the two can never stack. */}
      {user && !enrollmentRequired && <PostHogSurveyModal />}
    </div>
  )
}
