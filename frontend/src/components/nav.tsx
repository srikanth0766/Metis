import Link from "next/link";

const links: [string, string][] = [
  ["/", "interactive demo"],
  ["/about", "about & architecture"],
];

export function Nav() {
  return (
    <nav>
      <Link className="wordmark" href="/">metis</Link>
      <div className="nav-links">
        {links.map(([href, label]) => (
          <Link href={href} key={href}>{label}</Link>
        ))}
      </div>
    </nav>
  );
}
