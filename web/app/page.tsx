import RunPanel from "./components/RunPanel";

export default function Home() {
  return (
    <main className="page">
      <div className="hero">
        <div className="glow" />
        <div className="frame">
          <RunPanel />
        </div>
      </div>
    </main>
  );
}
