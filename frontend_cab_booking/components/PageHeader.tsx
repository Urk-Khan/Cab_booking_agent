export default function PageHeader({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="mb-6">
      <h1 className="font-head text-[22px] font-bold tracking-tight">{title}</h1>
      {description && (
        <p className="text-[13px] text-muted mt-1 max-w-[60ch]">{description}</p>
      )}
    </div>
  );
}
