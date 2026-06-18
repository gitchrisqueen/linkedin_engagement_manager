import { NavLink, Outlet } from 'react-router-dom'

const navLinks = [
  { to: '/', label: 'Dashboard', end: true },
  { to: '/account', label: 'Account' },
  { to: '/schedule', label: 'Schedule Post' },
  { to: '/review', label: 'Review Posts' },
]

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-100">
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 flex items-center gap-6 h-14">
          <span className="font-bold text-blue-600 text-lg">LEM</span>
          {navLinks.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-blue-600 border-b-2 border-blue-600 pb-0.5'
                    : 'text-gray-600 hover:text-gray-900'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </div>
      </nav>
      <main className="max-w-5xl mx-auto px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
