import { useQuery } from "@tanstack/react-query";
import { Package, FileText, Wrench, AlertTriangle, DollarSign, CheckCircle2 } from "lucide-react";

import { api } from "@/services/api";
import type { DashboardReport } from "@/types/api";
import { formatCurrency } from "@/lib/status-labels";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function StatCard({
  label,
  value,
  icon: Icon,
  tone = "default",
}: {
  label: string;
  value: string | number;
  icon: React.ElementType;
  tone?: "default" | "warning" | "danger" | "success";
}) {
  const toneClasses: Record<string, string> = {
    default: "bg-slate-100 text-slate-700",
    warning: "bg-amber-100 text-amber-700",
    danger: "bg-red-100 text-red-700",
    success: "bg-emerald-100 text-emerald-700",
  };

  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full ${toneClasses[tone]}`}>
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-xs text-slate-500">{label}</p>
          <p className="text-lg font-semibold text-slate-900">{value}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["reports", "dashboard"],
    queryFn: async () => (await api.get<DashboardReport>("/reports/dashboard")).data,
  });

  if (isLoading || !data) {
    return <p className="text-sm text-slate-500">Carregando...</p>;
  }

  return (
    <div>
      <PageHeader title="Dashboard" description="Visão geral da operação" />

      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
        <StatCard label="Equipamentos" value={data.equipamentos_total} icon={Package} />
        <StatCard label="Disponíveis" value={data.equipamentos_disponiveis} icon={CheckCircle2} tone="success" />
        <StatCard label="Alugados" value={data.equipamentos_alugados} icon={Package} />
        <StatCard label="Em manutenção" value={data.equipamentos_manutencao} icon={Wrench} tone="warning" />
        <StatCard label="Contratos ativos" value={data.contratos_ativos} icon={FileText} tone="success" />
        <StatCard label="Contratos vencidos" value={data.contratos_vencidos} icon={FileText} tone="warning" />
        <StatCard label="OS em aberto" value={data.ordens_servico_abertas} icon={Wrench} />
        <StatCard
          label="Faturas atrasadas"
          value={data.faturas_atrasadas_quantidade}
          icon={AlertTriangle}
          tone="danger"
        />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Receita recebida (mês atual)</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="flex items-center gap-2 text-2xl font-semibold text-emerald-700">
              <DollarSign className="h-6 w-6" /> {formatCurrency(data.receita_recebida_mes_atual)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Total em atraso</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="flex items-center gap-2 text-2xl font-semibold text-red-700">
              <AlertTriangle className="h-6 w-6" /> {formatCurrency(data.faturas_atrasadas_valor_total)}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
