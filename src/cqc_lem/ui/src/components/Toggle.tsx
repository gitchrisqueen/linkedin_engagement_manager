export default function Toggle({ on, onClick, ariaLabel }: { on: boolean; onClick: () => void; ariaLabel?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={ariaLabel}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 ${on ? 'bg-accent border-transparent' : 'bg-raised border-field'}`}
      role="switch"
      aria-checked={on}
    >
      <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full shadow-panel ring-0 transition duration-200 ease-in-out ${on ? 'translate-x-5 bg-raised' : 'translate-x-0 bg-field'}`} />
    </button>
  )
}
