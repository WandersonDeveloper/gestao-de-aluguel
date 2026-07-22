import { useQuery } from "@tanstack/react-query";

import { api } from "@/services/api";
import type { MostRentedEquipmentEntry, OverdueByClientEntry, RentalReport } from "@/types/api";
import { formatCurrency, formatDate } from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export function ReportsPage() {
  const { data: rental } = useQuery({
    queryKey: ["reports", "rentals"],
    queryFn: async () => (await api.get<RentalReport>("/reports/rentals")).data,
  });

  const { data: mostRented } = useQuery({
    queryKey: ["reports", "most-rented-equipment"],
    queryFn: async () =>
      (await api.get<MostRentedEquipmentEntry[]>("/reports/most-rented-equipment")).data,
  });

  const { data: overdue } = useQuery({
    queryKey: ["reports", "overdue-invoices"],
    queryFn: async () => (await api.get<OverdueByClientEntry[]>("/reports/overdue-invoices")).data,
  });

  return (
    <div>
      <PageHeader title="Relatórios" description="Locação, equipamentos mais alugados e inadimplência" />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Locação</CardTitle>
          </CardHeader>
          <CardContent>
            {rental ? (
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <p className="text-slate-500">Total de contratos</p>
                  <p className="text-lg font-semibold text-slate-900">{rental.total_contratos}</p>
                </div>
                <div>
                  <p className="text-slate-500">Valor total contratado</p>
                  <p className="text-lg font-semibold text-slate-900">{formatCurrency(rental.valor_total_contratado)}</p>
                </div>
                <div>
                  <p className="text-slate-500">Ativos</p>
                  <p className="text-slate-900">{rental.contratos_ativos}</p>
                </div>
                <div>
                  <p className="text-slate-500">Vencidos</p>
                  <p className="text-slate-900">{rental.contratos_vencidos}</p>
                </div>
                <div>
                  <p className="text-slate-500">Encerrados</p>
                  <p className="text-slate-900">{rental.contratos_encerrados}</p>
                </div>
                <div>
                  <p className="text-slate-500">Cancelados</p>
                  <p className="text-slate-900">{rental.contratos_cancelados}</p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">Carregando...</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Equipamentos mais alugados</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Equipamento</TableHead>
                  <TableHead>Locações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {mostRented?.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={2} className="text-center text-slate-500">
                      Sem dados ainda.
                    </TableCell>
                  </TableRow>
                )}
                {mostRented?.map((entry) => (
                  <TableRow key={entry.equipamento_id}>
                    <TableCell>{entry.equipamento_nome}</TableCell>
                    <TableCell>{entry.quantidade_locacoes}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Inadimplência por cliente</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {overdue?.length === 0 && <p className="text-sm text-slate-500">Nenhuma fatura em atraso.</p>}
            {overdue?.map((entry) => (
              <div key={entry.cliente_id} className="rounded-md border border-slate-200 p-3">
                <div className="mb-2 flex items-center justify-between">
                  <p className="font-medium text-slate-900">{entry.cliente_nome}</p>
                  <p className="text-sm text-red-700">
                    {entry.quantidade_faturas} fatura(s) — {formatCurrency(entry.total_atrasado)}
                  </p>
                </div>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Contrato</TableHead>
                      <TableHead>Vencimento</TableHead>
                      <TableHead>Valor</TableHead>
                      <TableHead>Multa</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {entry.faturas.map((fatura) => (
                      <TableRow key={fatura.invoice_id}>
                        <TableCell>#{fatura.contrato_id}</TableCell>
                        <TableCell>{formatDate(fatura.data_vencimento)}</TableCell>
                        <TableCell>{formatCurrency(fatura.valor)}</TableCell>
                        <TableCell>{formatCurrency(fatura.multa_juros_aplicado)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
