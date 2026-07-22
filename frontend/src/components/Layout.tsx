import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Package,
  Tags,
  Truck,
  FileText,
  Wrench,
  Receipt,
  BarChart3,
  UserCog,
  LogOut,
  Building2,
  Settings,
} from "lucide-react";

import { useAuth } from "@/context/AuthContext";
import { cn } from "@/lib/utils";

type NavItem = {
  to: string;
  label: string;
  icon: React.ElementType;
  end?: boolean;
};

type NavGroup = {
  label: string | null;
  items: NavItem[];
};

const navGroups: NavGroup[] = [
  {
    label: null,
    items: [{ to: "/", label: "Dashboard", icon: LayoutDashboard, end: true }],
  },
  {
    label: "Cadastros",
    items: [
      { to: "/clientes", label: "Clientes", icon: Users },
      { to: "/equipamentos", label: "Equipamentos", icon: Package },
      { to: "/categorias", label: "Categorias", icon: Tags },
      { to: "/filiais", label: "Filiais", icon: Building2 },
      { to: "/fornecedores", label: "Fornecedores", icon: Truck },
    ],
  },
  {
    label: "Operacional",
    items: [
      { to: "/contratos", label: "Contratos", icon: FileText },
      { to: "/ordens-servico", label: "Ordens de Serviço", icon: Wrench },
    ],
  },
  {
    label: "Financeiro",
    items: [{ to: "/faturas", label: "Faturas", icon: Receipt }],
  },
  {
    label: "Relatórios",
    items: [{ to: "/relatorios", label: "Relatórios", icon: BarChart3 }],
  },
];

const roleLabels: Record<string, string> = {
  admin: "Administrador",
  operador: "Operador",
  financeiro: "Financeiro",
};

function SidebarLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium text-slate-600 transition-colors hover:bg-slate-100 hover:text-slate-900",
          isActive && "bg-slate-900 text-white hover:bg-slate-900 hover:text-white",
        )
      }
    >
      <item.icon className="h-4 w-4 shrink-0" />
      {item.label}
    </NavLink>
  );
}

export function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      <aside className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white">
        <div className="flex h-14 items-center border-b border-slate-200 px-4">
          <span className="text-sm font-semibold text-slate-900">Gestão de Aluguéis</span>
        </div>
        <nav className="flex flex-1 flex-col gap-4 overflow-y-auto p-2 pt-3">
          {navGroups.map((group, index) => (
            <div key={group.label ?? `group-${index}`} className="flex flex-col gap-0.5">
              {group.label && (
                <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  {group.label}
                </p>
              )}
              {group.items.map((item) => (
                <SidebarLink key={item.to} item={item} />
              ))}
            </div>
          ))}
          {user?.papel === "admin" && (
            <div className="flex flex-col gap-0.5">
              <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                Administração
              </p>
              <SidebarLink item={{ to: "/usuarios", label: "Usuários", icon: UserCog }} />
              <SidebarLink item={{ to: "/configuracoes", label: "Configurações", icon: Settings }} />
            </div>
          )}
        </nav>
      </aside>

      <div className="flex flex-1 flex-col">
        <header className="flex h-14 items-center justify-end gap-3 border-b border-slate-200 bg-white px-6">
          <div className="text-right leading-tight">
            <p className="text-sm font-medium text-slate-900">{user?.nome}</p>
            <p className="text-xs text-slate-500">{user ? roleLabels[user.papel] : ""}</p>
          </div>
          <button
            onClick={logout}
            className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            title="Sair"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
