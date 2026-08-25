/**
 * The review window, shown to everyone.
 *
 * Urgency nobody can see does not motivate anyone, so the countdown is public.
 * Participation is shown alongside it so a thin round reads as thin rather than
 * hiding behind the word "reviewed".
 */
function fmt(iso) {
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export default function RoundBar({ round, isAuthor, onOpen, onExtend, busy }) {
  if (!round) {
    return isAuthor ? (
      <div className="roundbar">
        <span className="muted">
          No review window is open. Opening one sets a {14}-day deadline, which is also the moment
          to ask colleagues to look.
        </span>
        <button className="primary small" onClick={onOpen} disabled={busy}>Open review</button>
      </div>
    ) : null
  }

  const { open, days_left: left, comment_count: comments, reviewer_count: reviewers } = round
  const participation = `${reviewers} reviewer${reviewers === 1 ? '' : 's'}, ${comments} comment${comments === 1 ? '' : 's'}`
  const thin = open && left <= 3 && reviewers < 2

  return (
    <div className={`roundbar ${open ? 'open' : 'closed'}`}>
      {open ? (
        <span>
          <strong>Review closes in {left} day{left === 1 ? '' : 's'}</strong>
          <span className="muted"> · open since {fmt(round.opened_at)} · {participation}</span>
        </span>
      ) : (
        <span>
          <strong>Review window closed</strong>
          <span className="muted">
            {' '}· {fmt(round.opened_at)} to {fmt(round.closes_at)}
            {round.extensions > 0 && ` (extended ${round.extensions}×)`} · {participation}
          </span>
        </span>
      )}
      {isAuthor && open && round.extendable && (
        <button className="linkbtn" onClick={onExtend} disabled={busy}>Extend by a week</button>
      )}
      {isAuthor && !open && (
        <button className="primary small" onClick={onOpen} disabled={busy}>Open a new round</button>
      )}
      {isAuthor && thin && (
        <span className="nudge">
          Few people have commented. A direct message to three colleagues is the most effective
          thing you can do now.
        </span>
      )}
    </div>
  )
}
