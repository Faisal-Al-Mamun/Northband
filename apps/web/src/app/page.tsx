import { Brand, Button } from "@/components/ui/Button";

export default function LandingPage() {
  return (
    <main className="marketing">
      <header className="marketing-header">
        <Brand />
        <div className="header-actions">
          <Button href="/login" variant="ghost" size="sm">
            Sign in
          </Button>
          <Button href="/register" size="sm">
            Create account
          </Button>
        </div>
      </header>

      <section className="marketing-hero">
        <div>
          <p className="eyebrow">Full IELTS · Academic and General Training</p>
          <h1>See the band. Then see the work that moves it.</h1>
          <p className="lede">
            Timed Listening, Reading, Writing, and Speaking. Listening and Reading are marked from answer keys.
            Writing and Speaking get a practice band with quoted evidence — not an official IELTS score.
          </p>
          <div className="cta-row">
            <Button href="/register" variant="amber" size="lg">
              Start practising
            </Button>
            <Button href="/login" variant="ghost" size="lg">
              I already have an account
            </Button>
          </div>
        </div>
        <aside className="hero-preview" aria-hidden="true">
          <div className="preview-kicker">
            <span>Academic Writing Task 2</span>
            <span>Practice estimate</span>
          </div>
          <p className="preview-band">6.5</p>
          <p className="muted">Overall band · target 7.0</p>
          <div className="preview-grid">
            <div>
              <span>TR</span>
              <strong>6.0</strong>
            </div>
            <div>
              <span>CC</span>
              <strong>6.5</strong>
            </div>
            <div>
              <span>LR</span>
              <strong>7.0</strong>
            </div>
            <div>
              <span>GRA</span>
              <strong>6.5</strong>
            </div>
          </div>
        </aside>
      </section>

      <section className="section">
        <h2>Four skills, one studio.</h2>
        <p className="lede">The paper you will sit — not a form wizard.</p>
        <div className="feature-grid feature-grid-4">
          <article>
            <h3>Listening</h3>
            <p className="muted">Section audio, exam-once or practice replay. Marks from keys; transcript after submit.</p>
          </article>
          <article>
            <h3>Reading</h3>
            <p className="muted">Academic passages and GT sections. MCQ, TFNG, completion, short answer — key graded.</p>
          </article>
          <article>
            <h3>Writing</h3>
            <p className="muted">Task 1 and Task 2, Academic and GT. Four criteria, quoted evidence, exam-length ceilings.</p>
          </article>
          <article>
            <h3>Speaking</h3>
            <p className="muted">Parts 1–3 as in the exam: interview, cue-card long turn, then discussion. Local transcription, no Whisper API bill.</p>
          </article>
        </div>
      </section>

      <section className="section">
        <h2>How a Writing band is produced.</h2>
        <p className="lede">
          Models propose evidence. Python owns the number. Invented quotes never reach the report.
        </p>
        <ol className="pipeline">
          <li>
            <span className="pipeline-step">1</span>
            <div>
              <h3>Tools</h3>
              <p className="muted">Word count, coverage, overview, fillers — treated as facts the model may not contradict.</p>
            </div>
          </li>
          <li>
            <span className="pipeline-step">2</span>
            <div>
              <h3>Specialists</h3>
              <p className="muted">Writing and grammar agents return JSON only: proposed bands plus verbatim spans.</p>
            </div>
          </li>
          <li>
            <span className="pipeline-step">3</span>
            <div>
              <h3>Verifier</h3>
              <p className="muted">Any quote that is not in your text is dropped. Inflated grammar bands are capped.</p>
            </div>
          </li>
          <li>
            <span className="pipeline-step">4</span>
            <div>
              <h3>Python bands</h3>
              <p className="muted">Half-band math and exam ceilings. Then a coach list you can sit as the next drill.</p>
            </div>
          </li>
        </ol>
      </section>

      <section className="section">
        <h2>Leave with a plan, not a number.</h2>
        <p className="lede">The same criteria an examiner uses — then a closed loop back to the next timed attempt.</p>
        <div className="feature-grid">
          <article>
            <h3>Quoted evidence</h3>
            <p className="muted">Every comment is tied to language copied from your response. If the model invents a span, it is stripped — and the report shows the hit rate.</p>
          </article>
          <article>
            <h3>Study drills</h3>
            <p className="muted">Weakest criterion becomes an 8–20 minute task. Optional rewrite of one span about +0.5 band.</p>
          </article>
          <article>
            <h3>Re-sit delta</h3>
            <p className="muted">Sit the same prompt again and see criterion-level change, not a new chat thread.</p>
          </article>
        </div>
      </section>

      <footer className="footer">
        <span>Northband</span>
        <span>Estimates for practice only — not official IELTS results. Independent of the IELTS partners.</span>
      </footer>
    </main>
  );
}
