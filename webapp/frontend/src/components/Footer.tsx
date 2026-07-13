export function Footer() {
  return (
    <footer className="w-full px-margin-page py-gutter flex flex-col md:flex-row justify-between items-center gap-4 bg-surface-container-lowest border-t-thick border-black mt-12">
      <div className="flex flex-col md:items-start items-center">
        <span className="text-headline-md font-bold text-on-surface">JOBSPY</span>
        <span className="text-meta-xs uppercase tracking-widest text-secondary-fixed">
          RAW DATA. NO BULLSHIT.
        </span>
      </div>
      <div className="font-mono text-meta-xs uppercase tracking-widest text-outline">
        © {new Date().getFullYear()} JOBSPY ENGINE
      </div>
    </footer>
  );
}
