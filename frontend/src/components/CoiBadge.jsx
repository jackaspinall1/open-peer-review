const LABELS = {
  author: ['Author', 'coi-author'],
  coauthor: ['Co-author relationship found', 'coi-coauthor'],
  colleague: ['Same institution', 'coi-colleague'],
  none: ['No relationship found', 'coi-none'],
  unverifiable: ['Unverifiable', 'coi-grey'],
  pending: ['Verification pending', 'coi-grey'],
}

export default function CoiBadge({ coi }) {
  const [label, cls] = LABELS[coi?.status] ?? LABELS.pending
  return (
    <span className={`coibadge ${cls}`} title={coi?.detail ?? ''}>
      {label}
    </span>
  )
}

const EXPERTISE = {
  topic: ['Publishes on this topic', 'exp-strong'],
  subfield: ['Publishes in this subfield', 'exp-mid'],
  field: ['Publishes in this field', 'exp-mid'],
  none: ['No record in this area', 'coi-grey'],
  no_record: ['No publication record', 'coi-grey'],
}

export function ExpertiseBadge({ expertise }) {
  const entry = EXPERTISE[expertise?.level]
  if (!entry) return null // pending: say nothing rather than something wrong
  const [label, cls] = entry
  return (
    <span className={`coibadge ${cls}`} title={expertise?.detail ?? ''}>
      {label}
    </span>
  )
}
