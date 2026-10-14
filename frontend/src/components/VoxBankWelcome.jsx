import "./VoxBankWelcome.css";

export default function VoxBankWelcome({ onContinue }) {
  const sampleRecipients = [
    "Ravi Kumar",
    "Priya Sharma",
    "Rahul Reddy",
    "Chaithanya",
  ];

  return (
    <div
      className="voxbank-welcome-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="voxbank-welcome-title"
    >
      <section className="voxbank-welcome">
        <div className="voxbank-welcome-brand">
          <div className="voxbank-welcome-icon">V</div>
          <span>VoxBank</span>
          <span className="voxbank-prototype-badge">PROTOTYPE</span>
        </div>

        <p className="voxbank-eyebrow">VOICE-POWERED BANKING</p>

        <h1 id="voxbank-welcome-title">
          Banking conversations, made simpler.
        </h1>

        <p className="voxbank-welcome-description">
          Explore how a voice assistant can help you initiate a
          payment, review the details, and confirm your request
          through a guided conversation.
        </p>

        <div className="voxbank-welcome-section">
          <h2>How to use VoxBank</h2>

          <ol className="voxbank-steps">
            <li>
              <strong>Speak or type</strong>
              <span>
                Try: “Send 500 rupees to Rahul Reddy.” Use one of
                the four sample recipients listed below.
              </span>
            </li>
            <li>
              <strong>Review the payment</strong>
              <span>
                Check the recipient and amount carefully. Correct
                mistakes before proceeding.
              </span>
            </li>
            <li>
              <strong>Confirm or cancel</strong>
              <span>
                Confirm only when the displayed details are correct.
                Otherwise, cancel the request.
              </span>
            </li>
            <li>
              <strong>View the outcome</strong>
              <span>
                Review the result and reference number for a
                completed simulated transfer.
              </span>
            </li>
          </ol>
        </div>

        <div className="voxbank-prototype-notice">
          <strong>ⓘ Important: Prototype limitations</strong>

          <p>
            VoxBank is currently a demonstration prototype that uses
            mock banking data and a limited set of four sample
            recipients. It is not connected to real bank accounts.
          </p>

          <div className="voxbank-sample-recipients">
            <strong>Available sample recipients</strong>
            <ul>
              {sampleRecipients.map((recipient) => (
                <li key={recipient}>{recipient}</li>
              ))}
            </ul>
          </div>

          <p>
            <strong>Authentication is not implemented in this version.</strong>
            {" "}You can explore the voice-banking workflow without
            logging in, but this prototype does not provide real
            account security.
          </p>

          <p>
            All transfers are simulated and do not move real money.
            Do not enter real banking credentials, account passwords,
            PINs, or sensitive personal information. Speech recognition
            can make mistakes, so always review payment details before
            confirming.
          </p>

          <p>
            <strong>Coming soon:</strong> An updated version with
            authentication, enhanced security, and additional banking
            features is planned for a future release.
          </p>
        </div>

        <div className="voxbank-roadmap">
          <h2>Where we plan to take VoxBank</h2>

          <p>
            These are future plans, not features guaranteed by the
            current prototype.
          </p>

          <div className="voxbank-roadmap-grid">
            <article>
              <span>01</span>
              <strong>Authentication and secure banking</strong>
              <p>
                Add authentication, explore approved banking APIs,
                and introduce secure authorization and transaction
                controls.
              </p>
            </article>

            <article>
              <span>02</span>
              <strong>Stronger voice security</strong>
              <p>
                Improve replay and synthetic-voice detection,
                risk-based verification, and human handoff.
              </p>
            </article>

            <article>
              <span>03</span>
              <strong>Natural multilingual conversations</strong>
              <p>
                Expand English and Indian-language support, improve
                speech recognition, and clarify uncertain requests.
              </p>
            </article>

            <article>
              <span>04</span>
              <strong>Scalable infrastructure</strong>
              <p>
                Plan for monitoring, reliability, privacy controls,
                resilient services, and load testing.
              </p>
            </article>
          </div>
        </div>

        <button
          type="button"
          className="voxbank-continue-button"
          onClick={onContinue}
        >
          Continue to VoxBank <span aria-hidden="true">→</span>
        </button>

        <p className="voxbank-footer-note">
          Explore the prototype. Review every payment before confirming.
        </p>
      </section>
    </div>
  );
}
