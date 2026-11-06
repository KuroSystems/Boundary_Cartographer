import { Link } from 'react-router-dom';

// SourceIdLink (FE-06): evidence source references link to the evidence view.
export function SourceIdLink({ id }: { id: string }) {
  return (
    <Link className="mono source-id-link" to={`/evidence#${encodeURIComponent(id)}`}>
      {id}
    </Link>
  );
}
