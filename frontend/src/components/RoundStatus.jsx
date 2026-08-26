/**
 * Compact review-window status: a timeline showing how much of the window has
 * elapsed, plus the days remaining.
 *
 * Urgency that nobody can see motivates nobody, so this sits in the paper's
 * metadata line where it is always visible. Participation is in the tooltip and
 * in the closed-state label, so a thin round still reads as thin.
 */
const DAY = 86400000

function fmt(iso) {
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export default function RoundStatus({ round }) {
  if (!round) return null

  const opened = new Date(round.opened_at).getTime()
  const closes = new Date(round.closes_at).getTime()
  const elapsed = Math.min(1, Math.max(0, (Date.now() - opened) / (closes - opened)))
  const left = round.days_left
  const participation =
    `${round.reviewer_count} reviewer${round.reviewer_count === 1 ? '' : 's'}, ` +
    `${round.comment_count} comment${round.comment_count === 1 ? '' : 's'}`
  const title =
    `Review window ${fmt(round.opened_at)} to ${fmt(round.closes_at)}` +
    (round.extensions ? ` (extended ${round.extensions}×)` : '') +
    ` · ${participation}` +
    ` · ${Math.round((closes - opened) / DAY)} days total`

  return (
    <span className={`roundstatus ${round.open ? 'open' : 'closed'}`} title={title}>
      <span className="timeline" aria-hidden="true">
        <span className="timeline-fill" style={{ width: `${elapsed * 100}%` }} />
      </span>
      {round.open ? (
        <span className={left <= 3 ? 'urgent' : undefined}>
          {left} day{left === 1 ? '' : 's'} left
        </span>
      ) : (
        <span>Review closed · {participation}</span>
      )}
    </span>
  )
}
