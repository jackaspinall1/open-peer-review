/**
 * Privacy notice. Written to be specific rather than boilerplate: it names the
 * actual tables, the actual third parties, and the actual limit of the
 * pseudonymity promise, because a reviewer deciding how candid to be deserves
 * to know exactly what protection they have.
 */
export default function PrivacyPage() {
  return (
    <main className="page narrow prose">
      <h1>Privacy</h1>
      <p className="muted">Last updated 28 August 2026</p>

      <p>
        Open Peer Review is a non-commercial, public-good service. This note says what it does
        with personal data, in plain terms.
      </p>

      <h2>What is held</h2>
      <ul>
        <li>
          <strong>Your ORCID iD and name</strong>, received from ORCID when you sign in. We do not
          ask ORCID for your email address and do not have it, which is why this site cannot email
          you.
        </li>
        <li><strong>What you write</strong>: comments, replies, votes and reports.</li>
        <li>
          <strong>Your relationship to each paper you comment on</strong>: whether you are a listed
          author, have co-authored with one, share an institution, and whether you publish on the
          topic. This is derived from public records and stored so it need not be recomputed.
        </li>
        <li>
          <strong>A session cookie</strong>, signed, containing only an internal account number.
          There is no advertising, no third-party analytics or tracking of any kind, and no
          externally hosted fonts. Nothing about your visit leaves this server.
        </li>
        <li>
          <strong>Papers added here</strong>, including author names, ORCID iDs and affiliations
          that come with them from public scholarly records. Those authors may not use this site.
        </li>
        <li><strong>Server logs</strong>, which include IP addresses, kept only to operate the service.</li>
        <li>
          <strong>A count of how many times each paper is opened.</strong> A single number per
          paper, visible only to its authors, so they can tell whether anyone is arriving. Nothing
          about the visitor is recorded, no cookie is set for it, and it is not linked to you.
        </li>
      </ul>

      <h2>Pseudonymous, not anonymous</h2>
      <p>
        Your comments appear under a per-paper pseudonym such as “Reviewer 2”, or “Author” if you
        are listed on the paper. Other readers cannot tell who you are: the public interface never
        returns names, ORCID iDs, institutions or publication counts, and your pseudonym on one
        paper cannot be linked to your pseudonym on another.
      </p>
      <p>
        <strong>The operator can see who wrote what.</strong> The link between your ORCID iD and
        your comments is stored, because it is what makes the conflict-of-interest badges possible.
        It could also be disclosed if we were legally compelled to, for instance by a court order.
        We will not disclose it to authors, to employers, or on request.
      </p>
      <p>
        If that is not enough protection for what you want to say, do not post it here.
      </p>

      <h2>Who else sees your data</h2>
      <ul>
        <li><strong>ORCID</strong>, when you sign in, and when your public employment record is read for the “same institution” badge.</li>
        <li><strong>OpenAlex</strong>, which is queried using your ORCID iD to work out co-authorship and topical expertise.</li>
        <li><strong>Our hosting provider</strong>, which stores the data on our behalf.</li>
      </ul>
      <p>Nothing is sold, and nothing is shared for advertising.</p>

      <h2>Public, and lasting</h2>
      <p>
        Comments are visible to anyone with the link, including people who are not signed in.
        Deleting your own comment removes its text but leaves the thread in place, so replies to it
        remain readable.
      </p>
      <p>
        Completed review rounds are intended to be deposited as citable records with their own DOI.
        A deposited copy is permanent and outside our control, so it cannot be withdrawn afterwards.
      </p>

      <h2>Papers and their authors</h2>
      <p>
        Papers are added by their own authors, and author details come from public scholarly
        records. If you are a listed author of a paper here and want it taken down, ask and it will
        be removed.
      </p>

      <h2>Your choices</h2>
      <p>
        You can ask for a copy of what is held about you, ask for it to be corrected, delete your
        own comments, or ask for your account and comments to be removed. Some content may remain
        in a deposited review record, as described above.
      </p>

      <h2>Contact and jurisdiction</h2>
      <p>
        The operator is based in the United Kingdom and data is stored in London. Processing is on
        the basis of legitimate interests in running an open scholarly review service, and you may
        object at any time. Get in touch at{' '}
        <a href="mailto:CONTACT@EXAMPLE.COM">CONTACT@EXAMPLE.COM</a>.
      </p>
    </main>
  )
}
