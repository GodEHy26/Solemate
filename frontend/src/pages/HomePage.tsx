import { Link } from 'react-router-dom';

export function HomePage() {
  return (
    <div className="container">
      <section className="hero">
        <div>
          <span className="pill accent">Scan · Fit · Build</span>
          <h1 style={{ marginTop: 12 }}>Shoes made for the exact shape of your feet.</h1>
          <p className="lead">
            Sweep your phone around each foot, the way you set up Face ID. SoleMate turns the sweep into a 3D
            model of your foot, grades a custom last from it, and lets you pick every component, from a
            polyurethane or rubber outsole to a knit or cloth upper.
          </p>
          <div className="row mt">
            <Link to="/scan" className="btn primary lg">Scan my feet</Link>
            <Link to="/shoes" className="btn ghost lg">Browse shoes</Link>
          </div>
        </div>
        <div className="card surface">
          <h3 className="mb">How it works</h3>
          <div className="steps">
            <div className="step">
              <div>
                <strong>Top-down photo on paper.</strong>
                <p className="small">A sheet of A4 or Letter gives the scan its real-world scale.</p>
              </div>
            </div>
            <div className="step">
              <div>
                <strong>Orbit sweep.</strong>
                <p className="small">Move the phone around the foot until the ring fills, like a Face ID setup.</p>
              </div>
            </div>
            <div className="step">
              <div>
                <strong>3D contour and measurements.</strong>
                <p className="small">Length, ball and heel width, instep height, girths and a footprint outline.</p>
              </div>
            </div>
            <div className="step">
              <div>
                <strong>Configure and order.</strong>
                <p className="small">Choose outsole, midsole, upper, lining, insole and laces. The last is yours.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="grid mt">
        <div className="card">
          <h3>No special hardware</h3>
          <p className="small mt">Works in the browser with a normal phone camera. Depth-sensor meshes from a companion app can be uploaded too.</p>
        </div>
        <div className="card">
          <h3>A last, not a size</h3>
          <p className="small mt">Sizes are shown for orientation, but the shoe is built on a last graded and adjusted to your scan.</p>
        </div>
        <div className="card">
          <h3>Every component is a choice</h3>
          <p className="small mt">Materials carry grip, cushioning, breathability and durability ratings so trade-offs are visible.</p>
        </div>
      </section>
    </div>
  );
}
