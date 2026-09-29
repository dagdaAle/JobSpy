import { useId } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { Application, ApplicationStatus } from "../api/types";
import { STATUS_ITEMS } from "../lib/applications";

export function ApplicationFields({ value, onChange }: { value: Application; onChange: (value: Application) => void }) {
  const id = useId();
  const textField = (key: "applied_on" | "follow_up_on" | "cv_label" | "contact" | "next_step", label: string, type = "text", maxLength = 500) => (
    <div className="grid gap-2">
      <Label htmlFor={`${id}-${key}`}>{label}</Label>
      <Input id={`${id}-${key}`} type={type} maxLength={maxLength} value={value[key] ?? ""}
        onChange={(e) => onChange({ ...value, [key]: type === "date" ? e.target.value || null : e.target.value })} />
    </div>
  );
  return <div className="grid gap-4">
    <div className="grid gap-2">
      <Label htmlFor={`${id}-status`}>Stato</Label>
      <Select items={STATUS_ITEMS} value={value.status} onValueChange={(v) => v && onChange({ ...value, status: v as ApplicationStatus })}>
        <SelectTrigger id={`${id}-status`} className="w-full"><SelectValue /></SelectTrigger>
        <SelectContent>{STATUS_ITEMS.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}</SelectContent>
      </Select>
    </div>
    <div className="grid gap-4 sm:grid-cols-2">
      {textField("applied_on", "Data di invio", "date")}
      {textField("follow_up_on", "Data prossimo passo", "date")}
    </div>
    {textField("next_step", "Prossimo passo", "text", 2000)}
    {textField("contact", "Contatto / recruiter")}
    {textField("cv_label", "CV utilizzato (nome o versione)", "text", 300)}
    <div className="grid gap-2">
      <Label htmlFor={`${id}-notes`}>Note</Label>
      <Textarea id={`${id}-notes`} maxLength={10000} value={value.notes} onChange={(e) => onChange({ ...value, notes: e.target.value })} />
    </div>
  </div>;
}
