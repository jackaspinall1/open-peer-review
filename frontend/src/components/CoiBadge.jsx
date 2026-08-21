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
