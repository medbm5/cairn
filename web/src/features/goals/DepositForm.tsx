import { useState, type FormEvent } from 'react'
import { Field } from '../../components/Field'
import { SketchButton } from '../../components/sketch/SketchButton'
import { useToast } from '../../components/Toast'
import { formatMoney } from '../../lib/format'
import { useLanguage } from '../../lib/i18n'
import { useDeposit } from '../../lib/queries'
import { parseEuros } from '../onboarding/goalForm'
import { newIdempotencyKey } from './ledger'

/**
 * Deposit form. Each submission gets its own idempotency key; a retry after a network error
 * reuses it, so the same deposit can never be booked twice.
 */
export function DepositForm({ goalId }: { goalId: number }) {
  const { t, language } = useLanguage()
  const toast = useToast()
  const deposit = useDeposit(goalId)
  const [amount, setAmount] = useState('')
  const [error, setError] = useState<string>()
  const [key, setKey] = useState(newIdempotencyKey)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const cents = parseEuros(amount)
    if (cents === null || cents <= 0) {
      setError(t('errorTarget'))
      return
    }
    setError(undefined)
    deposit.mutate(
      { amountCents: cents, key },
      {
        onSuccess: () => {
          toast.show(t('depositDone', { amount: formatMoney(cents, language) }), 'success')
          setAmount('')
          setKey(newIdempotencyKey())
        },
        onError: (err) => setError(t('depositError', { message: err.message })),
      },
    )
  }

  return (
    <form onSubmit={submit} noValidate className="flex flex-wrap items-end gap-4">
      <Field
        label={t('depositLabel')}
        inputMode="decimal"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        error={error}
        className="w-48"
      />
      <SketchButton
        sketchId="deposit-submit"
        type="submit"
        variant="primary"
        disabled={deposit.isPending}
      >
        {deposit.isPending ? t('depositing') : t('depositButton')}
      </SketchButton>
    </form>
  )
}
