import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'
import { useAuth } from '../../contexts/useAuth'
import { DM_EVENTS } from './types'
import type { DmTemplate } from './types'
import { useRegisterSaveSection, sectionSaveCallbacks } from './settingsSave'
import PlaceholderChips from './PlaceholderChips'
import { FIELD_LIMITS } from './fieldLimits'
import { EVENTS, capture, maskProps } from '../../utils/analytics'

export default function DmTemplatesCard() {
  const { sessionToken } = useAuth()
  const queryClient = useQueryClient()
  // The edited list, once the user touches it — null means "show the API rows plus the blank
  // step-0 row every event needs". Derived rather than seeded in an effect, so a refetch can never
  // discard a template being typed.
  const [draft, setDraft] = useState<DmTemplate[] | null>(null)
  const [dmMsg, setDmMsg] = useState<{ ok: boolean; text: string } | null>(null)

  const { data: dmData } = useQuery({
    queryKey: ['dm-templates', sessionToken],
    queryFn: () =>
      api
        .get(`/user/dm-templates?session_token=${encodeURIComponent(sessionToken!)}`)
        .then((r) => r.data.detail as DmTemplate[]),
    enabled: !!sessionToken,
    staleTime: 60 * 1000,
  })
  // Every event gets a step-0 row to type into even when the API has none for it yet.
  const seeded = useMemo<DmTemplate[] | null>(() => {
    if (!dmData) return null
    const rows: DmTemplate[] = [...dmData]
    for (const ev of DM_EVENTS) {
      if (!rows.some((t) => t.event_type === ev.key && t.step === 0)) {
        rows.push({ event_type: ev.key, step: 0, delay_hours: 0, template_text: '', is_active: true })
      }
    }
    return rows
  }, [dmData])

  const dmTemplates: DmTemplate[] = draft ?? seeded ?? []
  const editTemplates = (fn: (ts: DmTemplate[]) => DmTemplate[]) =>
    setDraft((ts) => fn(ts ?? seeded ?? []))

  const updateTemplate = (event_type: string, step: number, patch: Partial<DmTemplate>) =>
    editTemplates((ts) => ts.map((t) => (t.event_type === event_type && t.step === step ? { ...t, ...patch } : t)))
  const addFollowupStep = (event_type: string) =>
    editTemplates((ts) => {
      const nextStep = ts.filter((t) => t.event_type === event_type).reduce((m, t) => Math.max(m, t.step), -1) + 1
      return [...ts, { event_type, step: nextStep, delay_hours: 24, template_text: '', is_active: true }]
    })
  const removeStep = (event_type: string, step: number) =>
    editTemplates((ts) => ts.filter((t) => !(t.event_type === event_type && t.step === step)))

  const dmMutation = useMutation({
    mutationFn: () =>
      api.put('/user/dm-templates', {
        session_token: sessionToken,
        templates: dmTemplates.filter((t) => t.template_text.trim()),
      }),
    onSuccess: async () => {
      // Wait for the refetch: React Query serves the pre-save rows until it lands, so dropping the
      // draft first would blank a template that was just written for the length of the round trip.
      await queryClient.invalidateQueries({ queryKey: ['dm-templates'] })
      setDraft(null)
      capture(EVENTS.dmTemplateSaved, {
        templates: dmTemplates.filter((t) => t.template_text.trim()).length,
        // How many events have a follow-up sequence configured, not the message bodies.
        followup_steps: dmTemplates.filter((t) => t.step > 0 && t.template_text.trim()).length,
      })
      setDmMsg({ ok: true, text: 'DM templates saved.' })
      setTimeout(() => setDmMsg(null), 3000)
    },
    onError: () => {
      setDmMsg({ ok: false, text: 'Could not save — try again.' })
      setTimeout(() => setDmMsg(null), 5000)
    },
  })

  const isDirty = !!seeded && JSON.stringify(dmTemplates) !== JSON.stringify(seeded)
  useRegisterSaveSection('dm-templates', 'DM Templates', isDirty,
    async () => { await dmMutation.mutateAsync(); return true })

  if (!seeded) return null

  return (
    <div className="bg-raised rounded-panel shadow-panel border border-hairline p-6 space-y-4">
      <h2 className="text-base font-semibold text-fg">DM Templates</h2>
      <p className="text-xs text-fg-muted">
        Blank uses the built-in default. Add follow-up steps to message again after a delay — the
        sequence stops automatically if they reply. Click a placeholder to insert it at your cursor:
      </p>
      <PlaceholderChips placeholders={[
        { token: '{first_name}', desc: "The recipient's first name" },
        { token: '{headline}', desc: "The recipient's headline / role" },
        { token: '{blog_url}', desc: 'Your configured blog URL' },
        { token: '{event_detail}', desc: 'The Catch-up milestone (e.g. "started a new position at Acme")' },
      ]} />
      {DM_EVENTS.map((ev) => {
        const steps = dmTemplates.filter((t) => t.event_type === ev.key).sort((a, b) => a.step - b.step)
        return (
          <div key={ev.key} className="border-t border-hairline pt-4">
            <p className="text-sm font-semibold text-fg">{ev.label}</p>
            {steps.map((t) => (
              <div key={t.step} className="mt-2 space-y-1">
                <div className="flex items-center gap-2 text-xs text-fg-muted">
                  <span>{t.step === 0 ? 'Initial message' : `Follow-up ${t.step}`}</span>
                  {t.step > 0 && (
                    <label className="flex items-center">
                      after
                      <input type="number" min={1} value={t.delay_hours}
                        onChange={(e) => updateTemplate(ev.key, t.step, { delay_hours: Number(e.target.value) })}
                        className="mx-1 w-16 border border-field rounded-control px-1 py-0.5" />
                      h
                    </label>
                  )}
                  {t.step > 0 && (
                    <button type="button" onClick={() => removeStep(ev.key, t.step)}
                      className="ml-auto text-danger hover:text-danger">Remove</button>
                  )}
                </div>
                <textarea value={t.template_text} rows={2} maxLength={FIELD_LIMITS.dm_template}
                  onChange={(e) => updateTemplate(ev.key, t.step, { template_text: e.target.value })}
                  placeholder="Leave blank for the default message"
                  {...maskProps('w-full border border-field rounded-panel px-3 py-2 text-sm')} />
              </div>
            ))}
            <button type="button" onClick={() => addFollowupStep(ev.key)}
              className="mt-2 text-xs text-accent font-medium hover:text-accent">+ Add follow-up</button>
          </div>
        )
      })}
      {dmMsg && (
        <p className={`text-sm font-medium ${dmMsg.ok ? 'text-success' : 'text-danger'}`}>{dmMsg.text}</p>
      )}
      <button type="button" onClick={() => dmMutation.mutate(undefined, sectionSaveCallbacks('dm-templates'))}
        disabled={dmMutation.isPending}
        className="w-full bg-accent text-white py-2 rounded-panel text-sm font-semibold hover:bg-accent/90 disabled:opacity-50 transition-colors">
        {dmMutation.isPending ? 'Saving…' : 'Save DM Templates'}
      </button>
    </div>
  )
}
