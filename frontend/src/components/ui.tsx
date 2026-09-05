import Link from "next/link";

export function Page({ eyebrow, title, children }: { eyebrow: string; title: string; children: React.ReactNode }) {
  return <main><p className="eyebrow">{eyebrow}</p><h1>{title}</h1>{children}</main>;
}

export function Action({ href, children }: { href: string; children: React.ReactNode }) {
  return <Link className="action" href={href}>{children}</Link>;
}
