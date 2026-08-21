export default function VoteButtons({ comment, onVote, disabled }) {
  const { up, down, mine } = comment.votes
  const cast = (v) => onVote(comment.id, mine === v ? 0 : v)
  return (
    <span className="votes">
      <button className={`votebtn ${mine === 1 ? 'cast' : ''}`} disabled={disabled} onClick={() => cast(1)} title="Helpful">
        ▲ {up}
      </button>
      <button className={`votebtn ${mine === -1 ? 'cast' : ''}`} disabled={disabled} onClick={() => cast(-1)} title="Not helpful">
        ▼ {down}
      </button>
    </span>
  )
}
