import CoiBadge, { ExpertiseBadge } from './CoiBadge'

/**
 * Shown in the sidebar while a paper has no comments.
 *
 * The empty space is the best place to explain how commenting works, and the
 * badges are easier to show than to describe, so these are the real components
 * rendered with example values.
 */
export default function CommentsGuide() {
  return (
    <div className="guide">
      <p>
        Select a sentence in the paper to comment on it, or leave a general comment about the
        paper as a whole.
      </p>

      <h3>Every comment carries its author's standing</h3>
      <p>
        Worked out from public records, so a reader can weigh a comment without knowing who wrote
        it. Their relationship to the paper's authors:
      </p>
      <div className="guidebadges">
        <span className="alias author">Author</span>
        <CoiBadge coi={{ status: 'coauthor' }} />
        <CoiBadge coi={{ status: 'colleague' }} />
        <CoiBadge coi={{ status: 'none' }} />
      </div>
      <p>and whether they publish in this area:</p>
      <div className="guidebadges">
        <ExpertiseBadge expertise={{ level: 'topic' }} />
        <ExpertiseBadge expertise={{ level: 'subfield' }} />
        <ExpertiseBadge expertise={{ level: 'none' }} />
      </div>

      <h3>Reviewers are pseudonymous</h3>
      <p>
        Comments appear as “Reviewer 1”, “Reviewer 2” and so on, numbered within this paper only.
        The same person is unlinkable across papers, so criticism does not depend on the seniority
        of whoever offers it.
      </p>

      <h3>Criticise the work, not the person</h3>
      <p>
        Say what is wrong with the argument, the method or the evidence. Describe what you observe
        rather than what you conclude about the authors.
      </p>
    </div>
  )
}
