import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { api } from "@/services/api";
import type { Client, Contract, Invoice } from "@/types/api";
import {
  contractStatusLabels,
  contractStatusVariant,
  formatCurrency,
  formatDate,
  invoiceStatusLabels,
  invoiceStatusVariant,
} from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Combobox } from "@/components/ui/combobox";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function InvoicesPage() {
  const [statusFilter, setStatusFilter] = useState<string>("todos");
  const [clienteFilter, setClienteFilter] = useState<string>("todos");

  const { data: invoices, isLoading } = useQuery({
    queryKey: ["invoices", statusFilter, clienteFilter],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (statusFilter !== "todos") params.status = statusFilter;
      if (clienteFilter !== "todos") params.cliente_id = clienteFilter;
      return (await api.get<Invoice[]>("/invoices", { params })).data;
    },
  });

  const { data: clients } = useQuery({
    queryKey: ["clients", "all"],
    queryFn: async () => (await api.get<Client[]>("/clients", { params: { limit: 500 } })).data,
  });

  const { data: contracts } = useQuery({
    queryKey: ["contracts", "all"],
    queryFn: async () => (await api.get<Contract[]>("/contracts", { params: { limit: 500 } })).data,
  });

  const clientsById = new Map((clients ?? []).map((c) => [c.id, c.nome]));
  const contractsById = new Map((contracts ?? []).map((c) => [c.id, c]));
  const clientOptions = (clients ?? []).map((c) => ({
    value: String(c.id),
    label: c.nome,
    searchText: c.documento,
  }));

  function clienteNomeDaFatura(invoice: Invoice): string {
    const contrato = contractsById.get(invoice.contrato_id);
    if (!contrato) return `Contrato #${invoice.contrato_id}`;
    return clientsById.get(contrato.cliente_id) ?? `Cliente #${contrato.cliente_id}`;
  }

  return (
    <div>
      <PageHeader title="Faturas" description="Cobranças geradas a partir dos contratos" />

      <div className="mb-4 flex items-center gap-2">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos os status</SelectItem>
            {Object.entries(invoiceStatusLabels).map(([value, label]) => (
              <SelectItem key={value} value={value}>
                {label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Combobox
          className="w-64"
          value={clienteFilter}
          onValueChange={setClienteFilter}
          placeholder="Todos os clientes"
          searchPlaceholder="Buscar por nome ou CNPJ/CPF..."
          options={[{ value: "todos", label: "Todos os clientes" }, ...clientOptions]}
        />
      </div>

      <div className="rounded-lg border border-slate-200 bg-white">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Cliente</TableHead>
              <TableHead>Contrato</TableHead>
              <TableHead>Vencimento</TableHead>
              <TableHead>Valor</TableHead>
              <TableHead>Multa</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading && (
              <TableRow>
                <TableCell colSpan={6} className="py-6 text-center text-slate-500">
                  Carregando...
                </TableCell>
              </TableRow>
            )}
            {!isLoading && invoices?.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-6 text-center text-slate-500">
                  Nenhuma fatura encontrada.
                </TableCell>
              </TableRow>
            )}
            {invoices?.map((invoice) => {
              const contrato = contractsById.get(invoice.contrato_id);
              return (
                <TableRow key={invoice.id}>
                  <TableCell className="font-medium text-slate-900">
                    <Link to={`/faturas/${invoice.id}`} className="hover:underline">
                      {clienteNomeDaFatura(invoice)}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <Link to={`/contratos/${invoice.contrato_id}`} className="hover:underline">
                      #{invoice.contrato_id}
                    </Link>
                    {contrato && (
                      <Badge variant={contractStatusVariant[contrato.status]} className="ml-2">
                        {contractStatusLabels[contrato.status]}
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>{formatDate(invoice.data_vencimento)}</TableCell>
                  <TableCell>{formatCurrency(invoice.valor)}</TableCell>
                  <TableCell>{formatCurrency(invoice.multa_juros_aplicado)}</TableCell>
                  <TableCell>
                    <Badge variant={invoiceStatusVariant[invoice.status]}>{invoiceStatusLabels[invoice.status]}</Badge>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
