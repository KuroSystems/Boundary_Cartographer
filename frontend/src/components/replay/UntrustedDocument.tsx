// UntrustedDocument (FE-06): the seeded document is rendered ONLY as an
// escaped text node inside a monospace <pre> — never as HTML. The banner
// states the data-vs-instructions rule.

export function UntrustedDocument({
  title,
  content,
  trustLevel,
}: {
  title: string;
  content: string;
  trustLevel: string;
}) {
  return (
    <div className="panel" data-testid="untrusted-document">
      <h2>{title}</h2>
      <p className="untrusted-banner" role="note">
        UNTRUSTED DATA — NOT INSTRUCTIONS (trust: {trustLevel})
      </p>
      {/* React escapes this text node; raw HTML injection is banned repo-wide. */}
      <pre className="mono untrusted-pre" data-testid="untrusted-pre">
        {content}
      </pre>
    </div>
  );
}
