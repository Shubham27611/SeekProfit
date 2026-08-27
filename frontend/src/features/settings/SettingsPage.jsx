import { useEffect, useState } from "react";
import { UserPlus, EnvelopeSimple, CircleNotch } from "@phosphor-icons/react";
import { PageHeader } from "@/components/shared/PageHeader";
import { SectionCard } from "@/components/shared/SectionCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import api, { apiError } from "@/lib/api";
import { useAuth } from "@/features/authentication/AuthContext";
import { PAGE } from "@/constants/testIds";

export const SettingsPage = () => {
    const { user } = useAuth();
    const [inviteEmail, setInviteEmail] = useState("");
    const [busy, setBusy] = useState(false);
    const [workspace, setWorkspace] = useState(null);

    const load = () => api.get("/workspace/me").then(({ data }) => setWorkspace(data.workspace));
    useEffect(() => { load(); }, []);

    const handleInvite = async (e) => {
        e.preventDefault();
        if (!inviteEmail.trim() || busy) return;
        setBusy(true);
        try {
            await api.post("/auth/invite", { email: inviteEmail.trim() });
            toast.success(`${inviteEmail} can now access this workspace on sign-in.`);
            setInviteEmail("");
            await load();
        } catch (err) {
            toast.error(apiError(err));
        } finally {
            setBusy(false);
        }
    };

    return (
        <div data-testid={PAGE.settings} className="sp-fade-in space-y-8">
            <PageHeader
                eyebrow="Settings"
                title="Workspace settings"
                description="Manage your workspace profile and lean-invite teammates. Deeper permissions and audit logs land next."
            />

            <div className="grid gap-6 lg:grid-cols-2">
                <SectionCard
                    title="Workspace"
                    description="These fields were set at onboarding"
                    bodyClassName="space-y-4"
                >
                    <div className="grid gap-4 sm:grid-cols-2">
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Name</p>
                            <p className="mt-2 text-sm text-foreground">{workspace?.name || "—"}</p>
                        </div>
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Industry</p>
                            <p className="mt-2 text-sm text-foreground">{workspace?.industry || "—"}</p>
                        </div>
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Currency</p>
                            <p className="mt-2 font-mono text-sm text-foreground">{workspace?.currency || "USD"}</p>
                        </div>
                        <div>
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">Owner</p>
                            <p className="mt-2 text-sm text-foreground">{user?.email}</p>
                        </div>
                    </div>
                </SectionCard>

                <SectionCard
                    title="Invite a teammate"
                    description="Lean invite — the first time they sign in with this email, they'll join this workspace."
                    bodyClassName="space-y-4"
                >
                    <form onSubmit={handleInvite} className="space-y-3">
                        <div className="space-y-2">
                            <Label htmlFor="invite-email" className="text-xs font-medium text-muted-foreground">Email</Label>
                            <Input
                                id="invite-email"
                                type="email"
                                value={inviteEmail}
                                onChange={(e) => setInviteEmail(e.target.value)}
                                placeholder="teammate@company.com"
                                data-testid="settings-invite-input"
                                className="h-10 border-border bg-background"
                            />
                        </div>
                        <Button
                            type="submit"
                            disabled={busy || !inviteEmail.trim()}
                            data-testid="settings-invite-submit"
                            className="bg-primary text-primary-foreground hover:bg-primary/90"
                        >
                            {busy ? <><CircleNotch size={14} weight="bold" className="animate-spin" />Sending…</> : <><UserPlus size={14} weight="bold" />Invite</>}
                        </Button>
                    </form>

                    {workspace?.invited_emails?.length > 0 && (
                        <div className="border-t border-border pt-4">
                            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                                Pending invites · {workspace.invited_emails.length}
                            </p>
                            <ul className="mt-2 space-y-1.5">
                                {workspace.invited_emails.map((e) => (
                                    <li
                                        key={e}
                                        data-testid={`settings-invite-row-${e}`}
                                        className="flex items-center gap-2 rounded-md border border-border bg-background px-3 py-2 text-xs"
                                    >
                                        <EnvelopeSimple size={12} weight="duotone" className="text-muted-foreground" />
                                        <span className="text-foreground">{e}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </SectionCard>
            </div>
        </div>
    );
};

export default SettingsPage;
