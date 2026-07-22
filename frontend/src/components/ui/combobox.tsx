import * as React from "react";
import { Check, ChevronsUpDown } from "lucide-react";

import { cn } from "@/lib/utils";

export type ComboboxOption = {
  value: string;
  label: string;
  /** Texto extra pesquisável (ex.: CNPJ/CPF), não exibido na lista fechada. */
  searchText?: string;
};

interface ComboboxProps {
  options: ComboboxOption[];
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  className?: string;
}

export function Combobox({
  options,
  value,
  onValueChange,
  placeholder = "Selecione...",
  searchPlaceholder = "Buscar por nome ou documento...",
  emptyMessage = "Nenhum resultado encontrado.",
  className,
}: ComboboxProps) {
  const [open, setOpen] = React.useState(false);
  const [search, setSearch] = React.useState("");
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const selected = options.find((o) => o.value === value);
  const normalizedSearch = search.trim().toLowerCase();
  const filtered = normalizedSearch
    ? options.filter(
        (o) =>
          o.label.toLowerCase().includes(normalizedSearch) ||
          o.searchText?.toLowerCase().includes(normalizedSearch),
      )
    : options;

  function handleSelect(optionValue: string) {
    onValueChange(optionValue);
    setOpen(false);
    setSearch("");
  }

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex h-9 w-full items-center justify-between rounded-md border border-slate-300 bg-white px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
      >
        <span className={cn("truncate text-left", !selected && "text-slate-400")}>
          {selected ? selected.label : placeholder}
        </span>
        <ChevronsUpDown className="h-4 w-4 shrink-0 text-slate-400" />
      </button>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-slate-200 bg-white shadow-md">
          <div className="border-b border-slate-100 p-1.5">
            <input
              autoFocus
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={searchPlaceholder}
              className="w-full rounded-sm px-2 py-1 text-sm outline-none placeholder:text-slate-400"
            />
          </div>
          <div className="max-h-60 overflow-y-auto p-1">
            {filtered.length === 0 && (
              <p className="px-2 py-1.5 text-sm text-slate-500">{emptyMessage}</p>
            )}
            {filtered.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => handleSelect(option.value)}
                className="flex w-full items-center justify-between rounded-sm px-2 py-1.5 text-left text-sm hover:bg-slate-100"
              >
                <span className="truncate">{option.label}</span>
                {option.value === value && <Check className="h-4 w-4 shrink-0 text-slate-900" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
