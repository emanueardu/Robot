/**
 * Google Apps Script para planificar tareas en la hoja "PROGRAMACION GENERAL".
 *
 * Características principales:
 *  - Revisa la carga semanal de cada colaborador considerando 20 h para TAREA y 11 h para PROYECTO/OBJETIVO.
 *  - Respeta la prioridad indicada en la columna "INDICE DE PRIORIDAD" y sobreasigna tareas críticas si es necesario.
 *  - Actualiza automáticamente las fechas de inicio/fin cuando cambian los estados.
 *  - Sincroniza la información con las pestañas de estado: BACKLOG, EN PROCESO, SEGUIMIENTO y FINALIZADA.
 *  - Pensado para ejecutarse cada 15 minutos mediante un activador de tiempo.
 */

const CONFIG = {
  mainSheet: 'PROGRAMACION GENERAL',
  statusSheets: ['BACKLOG', 'EN PROCESO', 'SEGUIMIENTO', 'FINALIZADA'],
  capacities: {
    TAREA: 20,
    PROYECTO: 11,
    OBJETIVO: 11,
    DEFAULT: 20
  },
  criticalityOrder: {
    CRITICA: 4,
    ALTA: 3,
    MEDIA: 2,
    BAJA: 1
  }
};

/**
 * Punto de entrada principal. Recalcula la planificación y replica los datos en las pestañas por estado.
 */
function updatePlanning() {
  const ss = SpreadsheetApp.getActive();
  const sheet = ss.getSheetByName(CONFIG.mainSheet);
  if (!sheet) {
    throw new Error('No se encontró la hoja "' + CONFIG.mainSheet + '".');
  }

  const values = sheet.getDataRange().getValues();
  if (values.length <= 1) {
    replicateStatusSheets(ss, values[0] || []);
    return;
  }

  const headers = values[0];
  const headerMap = buildHeaderMap(headers);
  validateHeaders(headerMap);

  const timezone = ss.getSpreadsheetTimeZone();
  const today = new Date();

  const processed = processRows(values.slice(1), headerMap, timezone, today);
  sheet.getRange(2, 1, processed.rows.length, headers.length).setValues(processed.rows);
  replicateStatusSheets(ss, headers, processed.statusBuckets);
}

/**
 * Procesa las filas del tablero principal y devuelve los datos listos para escribirse.
 */
function processRows(rows, headerMap, timezone, today) {
  const dataRows = rows.map(function (row) {
    return row.slice();
  });
  const weekStart = getWeekStart(today, timezone);
  const collaboratorLoad = {};
  const backlogTasks = [];
  const statusBuckets = {
    BACKLOG: [],
    'EN PROCESO': [],
    SEGUIMIENTO: [],
    FINALIZADA: []
  };

  for (let i = 0; i < dataRows.length; i++) {
    const row = dataRows[i];
    const estado = String(row[headerMap.ESTADO] || '').trim();
    const tipo = normalizeType(row[headerMap.TIPO]);
    const criticidad = String(row[headerMap.CRITICIDAD] || '').trim().toUpperCase();
    const colaborador = String(row[headerMap.COLABORADOR] || '').trim();
    const horas = toNumber(row[headerMap['HORAS ESTIMADAS']]);

    handleDatesForStatus(row, estado, headerMap, timezone, today);

    const weekCellValue = row[headerMap['SEMANA ASIGNADA']];
    const existingWeek = weekCellValue instanceof Date ? weekCellValue : (weekCellValue ? new Date(weekCellValue) : null);

    if (estado === 'EN PROCESO' || estado === 'SEGUIMIENTO') {
      const validWeek = existingWeek ? getWeekStart(existingWeek, timezone) : weekStart;
      row[headerMap['SEMANA ASIGNADA']] = new Date(validWeek.getTime());
      registerLoad(collaboratorLoad, colaborador, validWeek, tipo, horas, timezone);
    } else if (estado === 'FINALIZADA') {
      if (existingWeek instanceof Date) {
        row[headerMap['SEMANA ASIGNADA']] = new Date(getWeekStart(existingWeek, timezone).getTime());
      }
    } else if (estado === 'BACKLOG') {
      row[headerMap['SEMANA ASIGNADA']] = '';
      backlogTasks.push({
        rowIndex: i,
        row: row,
        tipo: tipo,
        prioridad: toNumber(row[headerMap['INDICE DE PRIORIDAD']]),
        criticidad: criticidad,
        colaborador: colaborador,
        horas: horas
      });
    }
  }

  allocateBacklog(backlogTasks, collaboratorLoad, weekStart, timezone, headerMap);

  dataRows.forEach(function (row) {
    const estado = String(row[headerMap.ESTADO] || '').trim();
    if (statusBuckets[estado]) {
      statusBuckets[estado].push(row.slice());
    }
  });

  return {
    rows: dataRows,
    statusBuckets: statusBuckets
  };
}

/**
 * Construye un diccionario Nombre de columna → Índice.
 */
function buildHeaderMap(headers) {
  const map = {};
  headers.forEach(function (name, idx) {
    if (!name) {
      return;
    }
    map[String(name).trim().toUpperCase()] = idx;
  });
  return map;
}

/**
 * Valida que las columnas mínimas existan en la hoja principal.
 */
function validateHeaders(map) {
  const required = [
    'ESTADO',
    'TIPO',
    'CRITICIDAD',
    'COLABORADOR',
    'HORAS ESTIMADAS',
    'SEMANA ASIGNADA',
    'INDICE DE PRIORIDAD',
    'FECHA INICIADA',
    'FECHA FINALIZADA'
  ];
  const missing = required.filter(function (key) {
    return !(key in map);
  });
  if (missing.length) {
    throw new Error('Faltan las siguientes columnas obligatorias: ' + missing.join(', '));
  }
}

/**
 * Normaliza el tipo de tarea a uno de los valores esperados.
 */
function normalizeType(value) {
  const text = String(value || '').trim().toUpperCase();
  if (text === 'PROYECTO' || text === 'OBJETIVO') {
    return text;
  }
  return 'TAREA';
}

/**
 * Se asegura de que las fechas de inicio/fin se actualicen según el estado.
 */
function handleDatesForStatus(row, estado, headerMap, timezone, today) {
  if (estado === 'EN PROCESO') {
    if (!(row[headerMap['FECHA INICIADA']] instanceof Date)) {
      row[headerMap['FECHA INICIADA']] = cloneDate(today, timezone);
    }
  } else if (estado === 'BACKLOG') {
    if (row[headerMap['FECHA INICIADA']] instanceof Date) {
      row[headerMap['FECHA INICIADA']] = '';
    }
  }

  if (estado === 'FINALIZADA') {
    if (!(row[headerMap['FECHA FINALIZADA']] instanceof Date)) {
      row[headerMap['FECHA FINALIZADA']] = cloneDate(today, timezone);
    }
  }
}

/**
 * Registra la carga horaria de un colaborador para una semana determinada.
 */
function registerLoad(loadMap, collaborator, weekDate, tipo, hours, timezone) {
  if (!collaborator) {
    return;
  }
  const weekKey = formatWeekKey(weekDate, timezone);
  if (!loadMap[collaborator]) {
    loadMap[collaborator] = {};
  }
  if (!loadMap[collaborator][weekKey]) {
    loadMap[collaborator][weekKey] = { TAREA: 0, PROYECTO: 0, OBJETIVO: 0 };
  }
  const taskType = normalizeType(tipo);
  loadMap[collaborator][weekKey][taskType] += hours;
}

/**
 * Distribuye las tareas del backlog considerando capacidades y prioridades.
 */
function allocateBacklog(backlogTasks, loadMap, weekStart, timezone, headerMap) {
  if (!backlogTasks.length) {
    return;
  }

  backlogTasks.sort(function (a, b) {
    const critA = CONFIG.criticalityOrder[a.criticidad] || 0;
    const critB = CONFIG.criticalityOrder[b.criticidad] || 0;
    if (critA !== critB) {
      return critB - critA;
    }
    return (b.prioridad || 0) - (a.prioridad || 0);
  });

  const maxWeeksToEvaluate = 52;

  backlogTasks.forEach(function (task) {
    if (!task.colaborador) {
      task.row[headerMap['SEMANA ASIGNADA']] = '';
      return;
    }

    const collaborator = task.colaborador;
    const taskType = normalizeType(task.tipo);
    const capacity = CONFIG.capacities[taskType] || CONFIG.capacities.DEFAULT;
    const totalHours = task.horas || 0;
    const isCritical = String(task.criticidad).toUpperCase() === 'CRITICA';

    let hoursRemaining = totalHours;
    let firstAssignedWeek = null;

    for (let weekOffset = 0; weekOffset < maxWeeksToEvaluate && hoursRemaining > 0; weekOffset++) {
      const candidateWeek = new Date(weekStart.getTime());
      candidateWeek.setDate(candidateWeek.getDate() + weekOffset * 7);
      const weekKey = formatWeekKey(candidateWeek, timezone);

      if (!loadMap[collaborator]) {
        loadMap[collaborator] = {};
      }
      if (!loadMap[collaborator][weekKey]) {
        loadMap[collaborator][weekKey] = { TAREA: 0, PROYECTO: 0, OBJETIVO: 0 };
      }

      const usedHours = loadMap[collaborator][weekKey][taskType] || 0;
      const remainingCapacity = capacity - usedHours;
      let chunk = 0;

      if (remainingCapacity > 0) {
        chunk = Math.min(remainingCapacity, hoursRemaining);
      }

      if (chunk === 0 && isCritical && weekOffset === 0 && hoursRemaining > 0) {
        chunk = hoursRemaining;
      }

      if (chunk > 0) {
        loadMap[collaborator][weekKey][taskType] = usedHours + chunk;
        if (!firstAssignedWeek) {
          firstAssignedWeek = new Date(candidateWeek.getTime());
        }
        hoursRemaining -= chunk;
      }
    }

    if (firstAssignedWeek) {
      task.row[headerMap['SEMANA ASIGNADA']] = firstAssignedWeek;
    } else {
      task.row[headerMap['SEMANA ASIGNADA']] = '';
    }
  });
}

/**
 * Replica los datos a las pestañas de estado.
 */
function replicateStatusSheets(ss, headers, statusBuckets) {
  CONFIG.statusSheets.forEach(function (sheetName) {
    let sheet = ss.getSheetByName(sheetName);
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
    }
    sheet.clearContents();
    if (headers && headers.length) {
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    }
    const rows = statusBuckets ? (statusBuckets[sheetName] || []) : [];
    if (rows.length) {
      sheet.getRange(2, 1, rows.length, headers.length).setValues(rows);
    }
  });
}

/**
 * Genera un activador para ejecutar la planificación cada 15 minutos.
 */
function createUpdateTrigger() {
  ScriptApp.newTrigger('updatePlanning').timeBased().everyMinutes(15).create();
}

/**
 * Devuelve el lunes de la semana de la fecha indicada respetando la zona horaria de la hoja.
 */
function getWeekStart(date, timezone) {
  const localDate = cloneDate(date, timezone);
  const day = localDate.getDay();
  const diff = (day === 0 ? -6 : 1) - day;
  localDate.setDate(localDate.getDate() + diff);
  localDate.setHours(0, 0, 0, 0);
  return localDate;
}

/**
 * Clona un objeto Date para evitar mutar la referencia original.
 */
function cloneDate(date, timezone) {
  const formatted = Utilities.formatDate(date, timezone, "yyyy-MM-dd'T'HH:mm:ss");
  return new Date(formatted);
}

/**
 * Convierte un valor arbitrario en número.
 */
function toNumber(value) {
  const num = Number(value);
  return isNaN(num) ? 0 : num;
}

/**
 * Devuelve una clave única (yyyy-MM-dd) para identificar semanas.
 */
function formatWeekKey(date, timezone) {
  const monday = getWeekStart(date, timezone);
  return Utilities.formatDate(monday, timezone, 'yyyy-MM-dd');
}
