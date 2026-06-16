const hiddenDisplayMenuNames = new Set([
  '若依官网'
])

function normalizeMenuName(name) {
  return String(name || '').replace(/\s+/g, '')
}

export function isHiddenDisplayMenuName(name) {
  return hiddenDisplayMenuNames.has(normalizeMenuName(name))
}

export function filterHiddenDisplayRoutes(routes = []) {
  return routes
    .filter(route => !isHiddenDisplayMenuName(route?.meta?.title))
    .map(route => {
      if (!route.children?.length) {
        return route
      }
      return {
        ...route,
        children: filterHiddenDisplayRoutes(route.children)
      }
    })
}

export function filterHiddenMenuRows(rows = []) {
  const childrenByParentId = new Map()
  rows.forEach(row => {
    const parentId = row.parentId ?? 0
    if (!childrenByParentId.has(parentId)) {
      childrenByParentId.set(parentId, [])
    }
    childrenByParentId.get(parentId).push(row)
  })

  const hiddenIds = new Set()
  function markHidden(row) {
    if (!row || hiddenIds.has(row.menuId)) {
      return
    }
    hiddenIds.add(row.menuId)
    ;(childrenByParentId.get(row.menuId) || []).forEach(markHidden)
  }

  rows.forEach(row => {
    if (isHiddenDisplayMenuName(row.menuName)) {
      markHidden(row)
    }
  })

  return rows.filter(row => !hiddenIds.has(row.menuId))
}
