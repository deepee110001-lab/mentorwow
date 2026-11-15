const ICE: RTCConfiguration = {
  iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
}

export type SignalPayload =
  | { kind: 'offer'; sdp: string }
  | { kind: 'answer'; sdp: string }
  | { kind: 'ice'; candidate: RTCIceCandidateInit }

export async function startPeer(options: {
  local: HTMLVideoElement
  remote: HTMLVideoElement
  initiator: boolean
  send: (payload: SignalPayload) => void
}) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true })
  options.local.srcObject = stream
  await options.local.play().catch(() => undefined)

  const pc = new RTCPeerConnection(ICE)
  stream.getTracks().forEach((track) => pc.addTrack(track, stream))
  pc.ontrack = (event) => {
    const [remoteStream] = event.streams
    if (remoteStream) {
      options.remote.srcObject = remoteStream
      options.remote.play().catch(() => undefined)
    }
  }
  pc.onicecandidate = (event) => {
    if (event.candidate) options.send({ kind: 'ice', candidate: event.candidate.toJSON() })
  }

  if (options.initiator) {
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    options.send({ kind: 'offer', sdp: offer.sdp ?? '' })
  }

  async function handle(payload: SignalPayload) {
    if (payload.kind === 'offer') {
      await pc.setRemoteDescription({ type: 'offer', sdp: payload.sdp })
      const answer = await pc.createAnswer()
      await pc.setLocalDescription(answer)
      options.send({ kind: 'answer', sdp: answer.sdp ?? '' })
    }
    if (payload.kind === 'answer') {
      await pc.setRemoteDescription({ type: 'answer', sdp: payload.sdp })
    }
    if (payload.kind === 'ice' && payload.candidate) {
      await pc.addIceCandidate(payload.candidate).catch(() => undefined)
    }
  }

  async function stats() {
    const report = await pc.getStats()
    let loss = 0
    let rtt = 0
    report.forEach((item) => {
      if (item.type === 'inbound-rtp' && 'packetsLost' in item) {
        loss += Number(item.packetsLost) || 0
      }
      if (item.type === 'candidate-pair' && item.state === 'succeeded') {
        rtt = Number(item.currentRoundTripTime || 0) * 1000
      }
    })
    return { loss, rtt }
  }

  function stop() {
    stream.getTracks().forEach((track) => track.stop())
    pc.close()
  }

  return { pc, handle, stats, stop }
}
