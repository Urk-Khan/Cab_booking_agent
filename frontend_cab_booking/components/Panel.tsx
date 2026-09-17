export default function Panel({
  title,
  action,
  children,
}: {
  title: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="border border-line bg-panel rounded-md overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-line">
        <h2 className="font-head text-[14px] font-semibold tracking-tight">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
