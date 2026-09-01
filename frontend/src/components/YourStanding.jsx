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
  const isAuthor = standing.coi.status === 'author'
  const checking = standing.coi.status === 'pending' || standing.expertise.level === 'pending'

  return (
    <div className="standing">
      <span className="muted">
        {standing.has_commented ? 'You appear here as' : 'Your comments will appear as'}
      </span>
      <span className={standing.coi.status === 'author' ? 'alias author' : 'alias'}>
        {standing.alias}
      </span>
      {checking && !isAuthor ? (
        <span className="muted">checking your relationship to this paper…</span>
      ) : (
        // An author needs neither badge: being on the paper already says both
        // that they are conflicted and that they work on the topic.
        !isAuthor && (
          <>
            <CoiBadge coi={standing.coi} />
            <ExpertiseBadge expertise={standing.expertise} />
          </>
        )
      )}
    </div>
  )
}
