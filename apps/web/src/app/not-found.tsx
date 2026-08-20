import { Button } from "@/components/ui/Button";

export default function NotFound() {
  return (
    <main className="not-found">
      <p className="eyebrow">404</p>
      <h1>This page is not on the paper.</h1>
      <p className="lede">The link may be out of date, or the attempt no longer exists.</p>
      <div className="btn-row">
        <Button href="/app">Go to studio</Button>
        <Button href="/" variant="ghost">
          Home
        </Button>
      </div>
    </main>
  );
}
