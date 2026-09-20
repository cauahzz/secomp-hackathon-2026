/**
 * Tipos derivados diretamente do contrato compartilhado (spec do ATLAS).
 * Qualquer mudança aqui precisa ser espelhada nas specs de API e Visão.
 */

export type Status = 'empty' | 'normal' | 'high' | 'over_limit' | 'no_data'

export interface Health {
  status: string
}

/* GET /structure */

export interface Campus {
  id: string
  name: string
}

export interface StructureSpace {
  id: string
  name: string
  code: string
  type: string
}

export interface StructureFloor {
  id: string
  name: string
  level: number
  spaces: StructureSpace[]
}

export interface StructureBuilding {
  id: string
  name: string
  code: string
  floors: StructureFloor[]
}

export interface Structure {
  campus: Campus
  buildings: StructureBuilding[]
}

/* GET /spaces */

export interface SpaceBuildingRef {
  id: string
  name: string
}

export interface SpaceFloorRef {
  id: string
  name: string
  level: number
}

export interface Space {
  id: string
  name: string
  code: string
  type: string
  building: SpaceBuildingRef
  floor: SpaceFloorRef
  capacity: number
  operational_limit: number | null
  /** null quando status === 'no_data' */
  person_count: number | null
  /** escala 0 a 1; null quando status === 'no_data' */
  occupancy_rate: number | null
  status: Status
  captured_at: string | null
}

/* GET /spaces/{id} */

export interface Source {
  camera_id: string
  camera_name: string
  region_id: string
  online: boolean
  last_seen_at: string | null
}

export interface SpaceDetail extends Space {
  source: Source
}

/* GET /spaces/{id}/occupancy */

export interface Occupancy {
  space_id: string
  person_count: number | null
  occupancy_rate: number | null
  status: Status
  captured_at: string | null
  source: Pick<Source, 'camera_id' | 'online' | 'last_seen_at'>
}

/* GET /spaces/{id}/history */

export interface HistoryPoint {
  captured_at: string
  person_count: number
  occupancy_rate: number
}

export interface History {
  space_id: string
  points: HistoryPoint[]
}

/* GET /summary */

export interface Summary {
  total_people: number
  spaces_total: number
  empty: number
  normal: number
  high: number
  over_limit: number
  no_data: number
  cameras_online: number
  cameras_total: number
  generated_at: string
}
