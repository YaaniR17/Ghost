const BACKEND = 'http://localhost:8000'

// Clock
function updateClock() {
  const now = new Date()
  const time = now.toLocaleTimeString('en-GB')
  document.getElementById('clock').textContent = time
  document.getElementById('vb-time').textContent = time
}
setInterval(updateClock, 1000)
updateClock()

// Add to feed
function addFeed(text, type = 'info') {
  const list = document.getElementById('feedList')
  const item = document.createElement('div')
  item.className = 'feed-item'
  item.innerHTML = `<span class="feed-tag ${type}">${type.toUpperCase()}</span><span class="feed-text">${text}</span>`
  list.prepend(item)
  if (list.children.length > 20) list.lastChild.remove()
}

// Send text to Ghost
async function sendText(text) {
  document.getElementById('userText').textContent = text
  document.getElementById('ghostText').textContent = '...'
  addFeed(`You: ${text}`, 'info')

  try {
    const res = await fetch(`${BACKEND}/think`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    })
    const data = await res.json()
    const reply = data.reply
    document.getElementById('ghostText').textContent = reply
    addFeed(`Ghost: ${reply}`, 'ok')

    // Speak the reply
    await fetch(`${BACKEND}/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: reply })
    })
  } catch (e) {
    addFeed('Error connecting to Ghost backend', 'warn')
    document.getElementById('ghostText').textContent = 'Backend offline.'
  }
}

// Voice button
let isListening = false
const talkBtn = document.getElementById('talkBtn')
const talkStatus = document.getElementById('talkStatus')
const talkWave = document.getElementById('talkWave')
const vsLabel = document.getElementById('vs-label')
const waveBars = document.querySelectorAll('.wave-bar')

async function startVoice() {
  if (isListening) return
  isListening = true

  talkBtn.textContent = '🔴 Listening...'
  talkBtn.classList.add('listening')
  talkStatus.textContent = 'Speak now — 5 seconds'
  talkWave.classList.add('active')
  vsLabel.textContent = 'Listening...'
  waveBars.forEach(b => b.classList.add('active'))

  try {
    const res = await fetch(`${BACKEND}/voice`, { method: 'POST' })
    const data = await res.json()

    if (data.transcript) {
      document.getElementById('userText').textContent = data.transcript
      addFeed(`You: ${data.transcript}`, 'info')
    }
    if (data.reply) {
      document.getElementById('ghostText').textContent = data.reply
      addFeed(`Ghost: ${data.reply}`, 'ok')
    }
    if (data.error) {
      addFeed(data.error, 'warn')
    }
  } catch (e) {
    addFeed('Error connecting to Ghost backend', 'warn')
  }

  isListening = false
  talkBtn.textContent = '🎙 TALK TO GHOST'
  talkBtn.classList.remove('listening')
  talkStatus.textContent = 'Click to speak'
  talkWave.classList.remove('active')
  vsLabel.textContent = 'Idle'
  waveBars.forEach(b => b.classList.remove('active'))
}

talkBtn.addEventListener('click', startVoice)
document.getElementById('tapBtn').addEventListener('click', startVoice)

// System stats (simulated)
function updateStats() {
  const cpu = Math.floor(Math.random() * 30 + 5)
  const ram = Math.floor(Math.random() * 20 + 50)
  document.getElementById('cpuVal').textContent = `${cpu}%`
  document.getElementById('ramVal').textContent = `${ram}%`
}
setInterval(updateStats, 3000)
updateStats()

// Check backend health on load
fetch(`${BACKEND}/health`)
  .then(r => r.json())
  .then(d => addFeed(d.status, 'ok'))
  .catch(() => addFeed('Backend offline — start the Python server', 'warn'))