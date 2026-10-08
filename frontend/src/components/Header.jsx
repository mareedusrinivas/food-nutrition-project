/**
 * Header — equivalent of the <header><h1>…</h1></header> block shared by
 * templates/index.html and templates/result.html.
 */
export default function Header({ title, subtitle }) {
  return (
    <header className="app-header">
      <h1>{title}</h1>
      {subtitle && <p className="app-header__subtitle">{subtitle}</p>}
    </header>
  );
}
