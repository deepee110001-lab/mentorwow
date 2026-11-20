import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { graphApi } from '../api'
import { Banner, Button, Field, Page, Text } from '../ui'

function localStamp(hoursAhead: number) {
  const d = new Date(Date.now() + hoursAhead * 3600000)
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

export function OrganizerNew() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [starts, setStarts] = useState(localStamp(0))
  const [ends, setEnds] = useState(localStamp(4))
  const [error, setError] = useState('')

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault()
    setError('')
    try {
      const event = await graphApi.createEvent({
        name,
        starts_at: new Date(starts).toISOString(),
        ends_at: new Date(ends).toISOString(),
      })
      navigate(`/organizer/events/${event.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create event')
    }
  }

  return (
    <Page>
      <Text variant="eyebrow">New event</Text>
      <Text variant="title">Create a room</Text>
      <Text variant="lede">Chat closes 24 hours after the event ends. The query feed closes after 7 days. Profiles stay.</Text>
      {error && <Banner>{error}</Banner>}
      <form className="form" style={{ maxWidth: 560, marginTop: 18 }} onSubmit={onSubmit}>
        <Field label="Event name">
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </Field>
        <Field label="Starts">
          <input type="datetime-local" value={starts} onChange={(e) => setStarts(e.target.value)} required />
        </Field>
        <Field label="Ends">
          <input type="datetime-local" value={ends} onChange={(e) => setEnds(e.target.value)} required />
        </Field>
        <Button type="submit">Create join link</Button>
      </form>
    </Page>
  )
}
