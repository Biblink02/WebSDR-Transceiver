<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  opacity: number
  color: string
  baseX: number  // Position de base pour l'effet de souris
  baseY: number
}

const container = ref<HTMLElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let animationFrameId: number | null = null
let mouseX = 0
let mouseY = 0
let isMouseInside = false

// Configuration des particules
const PARTICLE_COUNT = 260  // 30% de plus que 200
const CONNECTION_DISTANCE = 150
const PARTICLE_SPEED = 0.8  // Vitesse augmentée
const PARTICLE_SIZE_MIN = 1
const PARTICLE_SIZE_MAX = 3
const PARTICLE_OPACITY_MIN = 0.3
const PARTICLE_OPACITY_MAX = 0.7
const MOUSE_RADIUS = 100  // Rayon d'influence de la souris augmenté
const MOUSE_STRENGTH = 0.3  // Force d'interaction augmentée
const BASE_RETURN_STRENGTH = 0.02  // Force de retour à la position de base

let particles: Particle[] = []

function createParticle(width: number, height: number): Particle {
  const x = Math.random() * width
  const y = Math.random() * height
  return {
    x,
    y,
    baseX: x,  // Sauvegarder la position initiale
    baseY: y,
    vx: (Math.random() - 0.5) * PARTICLE_SPEED,
    vy: (Math.random() - 0.5) * PARTICLE_SPEED,
    size: Math.random() * (PARTICLE_SIZE_MAX - PARTICLE_SIZE_MIN) + PARTICLE_SIZE_MIN,
    opacity: Math.random() * (PARTICLE_OPACITY_MAX - PARTICLE_OPACITY_MIN) + PARTICLE_OPACITY_MIN,
    color: 'white'
  }
}

function initParticles() {
  if (!container.value) return
  const width = container.value.clientWidth
  const height = container.value.clientHeight

  particles = Array(PARTICLE_COUNT).fill(null).map(() => createParticle(width, height))
}

function drawParticle(ctx: CanvasRenderingContext2D, particle: Particle) {
  ctx.beginPath()
  ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2)
  ctx.fillStyle = `rgba(255, 255, 255, ${particle.opacity})`
  ctx.fill()
}

function drawConnections(ctx: CanvasRenderingContext2D) {
  for (let i = 0; i < particles.length; i++) {
    for (let j = i + 1; j < particles.length; j++) {
      const dx = particles[i].x - particles[j].x
      const dy = particles[i].y - particles[j].y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < CONNECTION_DISTANCE) {
        const opacity = (1 - distance / CONNECTION_DISTANCE) * 0.2
        ctx.beginPath()
        ctx.moveTo(particles[i].x, particles[i].y)
        ctx.lineTo(particles[j].x, particles[j].y)
        ctx.strokeStyle = `rgba(255, 255, 255, ${opacity})`
        ctx.stroke()
      }
    }
  }
}

function updateParticles(width: number, height: number) {
  particles.forEach(particle => {
    // Mouvement de base
    particle.x += particle.vx
    particle.y += particle.vy

    // Effet de souris
    if (isMouseInside) {
      const dx = mouseX - particle.x
      const dy = mouseY - particle.y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance < MOUSE_RADIUS) {
        const force = (MOUSE_RADIUS - distance) / MOUSE_RADIUS
        particle.x -= dx * force * MOUSE_STRENGTH
        particle.y -= dy * force * MOUSE_STRENGTH
      }
    }

    // Mouvement constant
    particle.baseX += particle.vx
    particle.baseY += particle.vy

    // Retour progressif à la position de base après interaction souris
    if (isMouseInside) {
      particle.x += (particle.baseX - particle.x) * BASE_RETURN_STRENGTH
      particle.y += (particle.baseY - particle.y) * BASE_RETURN_STRENGTH
    } else {
      particle.x = particle.baseX
      particle.y = particle.baseY
    }

    // Rebond sur les bords
    if (particle.x < 0 || particle.x > width) particle.vx *= -1
    if (particle.y < 0 || particle.y > height) particle.vy *= -1

    // Maintenir les particules dans les limites
    particle.x = Math.max(0, Math.min(width, particle.x))
    particle.y = Math.max(0, Math.min(height, particle.y))
  })
}

function animate() {
  if (!ctx || !container.value) return

  const width = container.value.clientWidth
  const height = container.value.clientHeight

  ctx.clearRect(0, 0, width, height)

  updateParticles(width, height)
  drawConnections(ctx)
  particles.forEach(particle => drawParticle(ctx, particle))

  animationFrameId = requestAnimationFrame(animate)
}

function handleResize() {
  if (!container.value || !ctx?.canvas) return

  const canvas = ctx.canvas
  canvas.width = container.value.clientWidth
  canvas.height = container.value.clientHeight

  // Réinitialiser les particules avec les nouvelles dimensions
  initParticles()
}

function handleMouseMove(event: MouseEvent) {
  if (!container.value) return
  const rect = container.value.getBoundingClientRect()
  mouseX = event.clientX - rect.left
  mouseY = event.clientY - rect.top
  isMouseInside = true
}


onMounted(() => {
  if (!container.value) return

  const canvas = document.createElement('canvas')
  canvas.width = container.value.clientWidth
  canvas.height = container.value.clientHeight
  container.value.appendChild(canvas)

  ctx = canvas.getContext('2d')
  if (!ctx) return

  initParticles()
  window.addEventListener('resize', handleResize)
  document.addEventListener('mousemove', handleMouseMove)
  animate()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  document.removeEventListener('mousemove', handleMouseMove)
  if (animationFrameId !== null) {
    cancelAnimationFrame(animationFrameId)
  }
})
</script>

<template>
  <div ref="container" class="particles-container"></div>
</template>

<style scoped>
.particles-container {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  background: rgb(0,8,20);
  overflow: hidden;
  cursor: none;
  margin: 0;
  padding: 0;
}

.particles-container canvas {
  display: block;
  width: 100%;
  height: 100%;
}
</style>
