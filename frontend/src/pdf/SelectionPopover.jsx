export default function SelectionPopover({ popover, onComment }) {
  if (!popover) return null
  const top = Math.min(popover.y + 8, window.innerHeight - 48)
  const left = Math.min(popover.x, window.innerWidth - 140)
  return (
    <button className="selpopover" style={{ top, left }} onMouseDown={(e) => { e.preventDefault(); e.stopPropagation() }} onClick={onComment}>
      💬 Comment
    </button>
  )
}
