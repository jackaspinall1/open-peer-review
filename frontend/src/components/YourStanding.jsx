import CoiBadge, { ExpertiseBadge } from './CoiBadge'

/**
 * How the signed-in reader will be labelled if they comment here.
 *
 * Shown before they write rather than after: people should know how they will
 * appear before deciding what to say, and discovering "co-author relationship
 * found" underneath a comment you have already posted is a poor way to learn
 * how the system works.
 */
export default function YourStanding({ standing }) {
  if (!standing) return null
  const checking = standing.coi.status === 'pending' || standing.expertise.level === 'pending'

  return (
    <div className="standing">
      <span className="muted">
        {standing.has_commented ? 'You appear here as' : 'Your comments will appear as'}
      </span>
      <span className={standing.coi.status === 'author' ? 'alias author' : 'alias'}>
        {standing.alias}
      </span>
      {checking ? (
        <span className="muted">checking your relationship to this paper…</span>
      ) : (
        <>
          {standing.coi.status !== 'author' && <CoiBadge coi={standing.coi} />}
          <ExpertiseBadge expertise={standing.expertise} />
        </>
      )}
    </div>
  )
}
