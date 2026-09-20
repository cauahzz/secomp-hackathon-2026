'use client'

import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'

type MapState = 'loading' | 'ready' | 'missing'

export interface SvgMapProps {
  /** Caminho do SVG em /public/maps, ex.: /maps/bld-1-f2.svg */
  src: string
  /** IDs que existem no SVG e têm dado correspondente. */
  interactiveIds: string[]
  /** Cor de preenchimento por ID; null deixa o elemento neutro. */
  fillFor: (id: string) => string | null
  /** Texto lido por leitor de tela ao focar o elemento. */
  labelFor: (id: string) => string
  tooltipFor: (id: string) => ReactNode
  selectedId?: string | null
  onSelect: (id: string) => void
  /** Classe da moldura do desenho; o fallback não a herda e cresce sozinho. */
  className?: string
  /** Renderizado quando o SVG daquele nível ainda não foi desenhado. */
  fallback: ReactNode
}

const SHAPE_SELECTOR = 'path, rect, polygon, circle, ellipse'

/** Folga usada para manter o tooltip dentro da moldura do mapa. */
const TOOLTIP_WIDTH = 232
const TOOLTIP_HEIGHT = 96
const POINTER_OFFSET = 14

/** Preenche o próprio elemento e, se for um grupo, as formas dentro dele. */
function paintShape(element: SVGElement, fill: string, stroke: string, strokeWidth: string) {
  const targets: SVGElement[] =
    element.tagName === 'g'
      ? Array.from(element.querySelectorAll<SVGElement>(SHAPE_SELECTOR))
      : [element]

  for (const target of targets) {
    target.style.fill = fill
    target.style.stroke = stroke
    target.style.strokeWidth = strokeWidth
    // A cor vem do polling: sem transição o ambiente troca de status num salto.
    target.style.transition = 'fill 240ms var(--ease-out), stroke 240ms var(--ease-out)'
  }
}

/** Remontar a cada `src` deixa o estado de carregamento nascer limpo. */
export function SvgMap(props: SvgMapProps) {
  return <SvgMapView key={props.src} {...props} />
}

/**
 * Carrega o SVG inline (não como <img>) para poder colorir e clicar nos
 * elementos pelo id. O mapa não guarda ocupação: só geometria e IDs.
 */
function SvgMapView({
  src,
  interactiveIds,
  fillFor,
  labelFor,
  tooltipFor,
  selectedId,
  onSelect,
  className = '',
  fallback,
}: SvgMapProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [markup, setMarkup] = useState<string | null>(null)
  const [state, setState] = useState<MapState>('loading')
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [pointer, setPointer] = useState({ x: 0, y: 0 })

  useEffect(() => {
    let active = true

    fetch(src)
      .then((response) => (response.ok ? response.text() : Promise.reject(response.status)))
      .then((text) => {
        if (!active) return
        // Um 404 do Next volta como página HTML; sem <svg> não há mapa.
        if (!text.includes('<svg')) throw new Error('resposta não é um SVG')
        setMarkup(text)
        setState('ready')
      })
      .catch(() => {
        if (active) setState('missing')
      })

    return () => {
      active = false
    }
  }, [src])

  // Acessibilidade e ponteiro: só os elementos com dado correspondente reagem.
  useEffect(() => {
    const container = containerRef.current
    if (!container || state !== 'ready') return

    // Sem width/height fixos o viewBox volta a mandar; o resto é a classe
    // .map-surface, que limita a altura sem distorcer o traçado.
    const svg = container.querySelector('svg')
    if (svg) {
      svg.removeAttribute('width')
      svg.removeAttribute('height')
    }

    for (const id of interactiveIds) {
      const element = container.querySelector<SVGElement>(`#${CSS.escape(id)}`)
      if (!element) continue
      element.dataset.interactive = 'true'
      element.setAttribute('role', 'button')
      element.setAttribute('tabindex', '0')
      element.style.cursor = 'pointer'
      element.style.touchAction = 'manipulation'
      element.style.transition = 'opacity 120ms var(--ease-out)'
    }
  }, [markup, state, interactiveIds])

  // Pintura: roda a cada ciclo de polling, pois as cores vêm do status.
  useEffect(() => {
    const container = containerRef.current
    if (!container || state !== 'ready') return

    // Só os candidatos marcados pelo desenho são repintados: o resto do SVG
    // (paredes, textos, fundo) fica como o autor desenhou.
    const candidates = container.querySelectorAll<SVGElement>(
      '.atlas-space, .atlas-building, [data-interactive="true"]',
    )

    for (const element of candidates) {
      const fill = element.id ? fillFor(element.id) : null

      if (fill === null) {
        // Elemento do SVG sem ambiente correspondente: neutro.
        paintShape(element, 'var(--map-inactive)', 'var(--map-stroke)', '1')
        element.style.opacity = '1'
        element.style.filter = 'none'
        continue
      }

      const isSelected = element.id === selectedId
      paintShape(
        element,
        fill,
        isSelected ? 'var(--map-selected)' : 'var(--map-stroke)',
        // As paredes são desenhadas por cima e comem metade do traço; 4 deixa
        // 2 px visíveis dentro do ambiente.
        isSelected ? '4' : '1',
      )
      // O brilho é o que acha o ambiente selecionado numa planta cheia de traço.
      element.style.filter = isSelected ? 'drop-shadow(0 0 10px var(--map-selected))' : 'none'
      // Opacidade 0.85 no mapa, como manda a spec; o hover acende o ambiente.
      element.style.opacity = hoveredId === element.id ? '1' : '0.85'
      element.setAttribute('aria-label', labelFor(element.id))
    }
  }, [markup, state, fillFor, labelFor, selectedId, hoveredId])

  const findInteractive = useCallback((target: EventTarget | null): string | null => {
    if (!(target instanceof Element)) return null
    const element = target.closest('[data-interactive="true"]')
    return element?.id ?? null
  }, [])

  if (state === 'missing') return <>{fallback}</>

  return (
    <div className={`relative w-full ${className}`}>
      {state === 'loading' && (
        <div className="absolute inset-0 animate-pulse rounded-lg bg-surface-2" aria-busy="true" />
      )}

      <div
        ref={containerRef}
        className="w-full"
        onClick={(event) => {
          const id = findInteractive(event.target)
          if (id) onSelect(id)
        }}
        onKeyDown={(event) => {
          if (event.key !== 'Enter' && event.key !== ' ') return
          const id = findInteractive(event.target)
          if (!id) return
          event.preventDefault()
          onSelect(id)
        }}
        onPointerMove={(event) => {
          // No toque um único pointermove dispara antes do clique e deixaria o
          // tooltip preso na tela; ali o próprio toque já abre o destino.
          if (event.pointerType !== 'mouse') return
          const bounds = event.currentTarget.getBoundingClientRect()
          const x = event.clientX - bounds.left + POINTER_OFFSET
          const y = event.clientY - bounds.top + POINTER_OFFSET
          setPointer({
            x: Math.max(8, Math.min(x, bounds.width - TOOLTIP_WIDTH)),
            y: Math.max(8, Math.min(y, bounds.height - TOOLTIP_HEIGHT)),
          })
          setHoveredId(findInteractive(event.target))
        }}
        onPointerLeave={() => setHoveredId(null)}
        dangerouslySetInnerHTML={markup ? { __html: markup } : undefined}
      />

      {hoveredId && (
        <div
          role="tooltip"
          className="pointer-events-none absolute z-20 max-w-56 rounded-md border border-border bg-surface px-3 py-2 text-xs shadow-lg"
          style={{ left: pointer.x, top: pointer.y }}
        >
          {tooltipFor(hoveredId)}
        </div>
      )}
    </div>
  )
}
