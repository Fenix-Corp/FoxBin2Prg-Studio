*========================================================================
* fb2p_bridge.prg
* Driver VFP para FoxBin2Prg-Studio.
*
* Lee un job INI cuya ruta viene por la variable de entorno FB2P_JOB,
* usa el Object API (c_foxbin2prg) para ejecutar cada operacion capturando
* la excepcion, y emite un stream de eventos JSONL al archivo indicado en
* la clave 'eventStream' del job.
*
* Protocolo: docs/ARCHITECTURE.md
*
* Nunca abre dialogos: pasa siempre cDontShowErrors=1 y cDontShowProgress=1,
* y sanea el cType para eliminar INTERACTIVE / SHOWMSG.
*========================================================================
LPARAMETERS tcJobFileOverride

LOCAL lcJobFile, lcJobBody, loJob, loSection, loFB, loEx
LOCAL lcHome, lcFB2P, lcEventFile, lnDryRun, lcFB2PVer, lcVFPVer
LOCAL lcOpId, lcFile, lcType, lcOutFolder
LOCAL lnI, lnJ, lnCnt, lnStart, lnElapsed, lnRet, lnGlobalStart
LOCAL lnOkCount, lnErrCount
LOCAL ARRAY laProcs[1, 6]

lcJobFile = IIF(EMPTY(tcJobFileOverride), GETENV("FB2P_JOB"), tcJobFileOverride)

IF EMPTY(lcJobFile) OR NOT FILE(lcJobFile)
    ? "FB2P_BRIDGE ERROR: FB2P_JOB no definido o archivo inexistente: " + TRANSFORM(lcJobFile)
    QUIT
ENDIF

lcJobBody = FILETOSTR(lcJobFile)
loJob = parse_ini(lcJobBody)

lcHome      = get_val(loJob, "job", "foxbin2prghome", "")
lcEventFile = get_val(loJob, "job", "eventstream", "")
lnDryRun    = VAL(get_val(loJob, "job", "dryrun", "0"))

IF EMPTY(lcEventFile)
    ? "FB2P_BRIDGE ERROR: eventStream ausente en job"
    QUIT
ENDIF

* Reset del archivo de eventos (empieza vacio)
STRTOFILE("", lcEventFile, 0)

IF EMPTY(lcHome)
    emit_driver_error(lcEventFile, "foxbin2prgHome ausente en job", "config")
    QUIT
ENDIF

lcFB2P = ADDBS(lcHome) + "FoxBin2Prg.EXE"
IF NOT FILE(lcFB2P)
    lcFB2P = ADDBS(lcHome) + "FoxBin2Prg.FXP"
ENDIF
IF NOT FILE(lcFB2P)
    emit_driver_error(lcEventFile, "No se encontro FoxBin2Prg (EXE/FXP) en " + lcHome, "discovery")
    QUIT
ENDIF

loFB = NULL
TRY
    SET PROCEDURE TO (lcFB2P) ADDITIVE
    loFB = CREATEOBJECT("c_foxbin2prg")
CATCH TO loEx
    emit_driver_error(lcEventFile, ;
        "Fallo instanciando c_foxbin2prg: " + loEx.Message + ;
        " (linea " + TRANSFORM(loEx.LineNo) + ")", "instantiate")
    QUIT
ENDTRY

* Version de FoxBin2Prg: leemos foxbin2prg.pj2 (o cualquier .*2 del home),
* que contiene el tag "Version=\"1.21\"" en la cabecera. VERNO pass-by-ref
* no devuelve la version en algunos builds, este metodo es 100% confiable.
lcFB2PVer = detect_fb2p_version(lcHome)

lcVFPVer = VERSION(4)

lnGlobalStart = SECONDS()
emit_event(lcEventFile, ;
    '{"event":"job_start"' + ;
    ',"total":' + TRANSFORM(loJob.op_count) + ;
    ',"timestamp":"' + iso_now() + '"' + ;
    ',"vfpVersion":"' + json_esc(lcVFPVer) + '"' + ;
    ',"fb2pVersion":"' + json_esc(lcFB2PVer) + '"' + ;
    ',"dryRun":' + TRANSFORM(lnDryRun) + '}')

lnOkCount  = 0
lnErrCount = 0

FOR lnI = 1 TO loJob.op_count
    loSection = loJob.op_at(lnI)
    IF ISNULL(loSection)
        LOOP
    ENDIF

    lcOpId = loSection.op_id
    lcFile = loSection.get_value("file", "")
    lcType = sanitize_ctype(loSection.get_value("type", ""))

    emit_event(lcEventFile, ;
        '{"event":"op_start"' + ;
        ',"opId":"' + json_esc(lcOpId) + '"' + ;
        ',"file":"' + json_esc(lcFile) + '"' + ;
        ',"direction":"' + json_esc(lcType) + '"}')

    lnStart = SECONDS()
    lnRet   = -1
    STORE NULL TO loEx

    TRY
        loFB.l_ProcessFiles = IIF(lnDryRun == 1, .F., .T.)
        loFB.clearProcessedFiles()

        lcOutFolder = loSection.get_value("outputFolder", "")
        loFB.c_OutputFile = lcOutFolder

        lnRet = loFB.execute( ;
            lcFile, ;                                        && cInputFile
            lcType, ;                                        && cType
            "", ;                                            && cTextName (SCC)
            "", ;                                            && lGenText  (SCC)
            "1", ;                                           && cDontShowErrors (FORZADO)
            loSection.get_value("debug", "0"), ;             && cDebug
            "1", ;                                           && cDontShowProgress (FORZADO)
            NULL, ;                                          && oModule
            NULL, ;                                          && oEx (usamos TRY/CATCH externo)
            .F., ;                                           && lRelanzarError
            "", ;                                            && cOriginalFileName
            loSection.get_value("recompile", "1"), ;         && cRecompile
            loSection.get_value("noTimestamps", "1"), ;      && cNoTimestamps
            loSection.get_value("backupLevels", "1"), ;      && cBackupLevels
            loSection.get_value("clearUniqueID", "1"), ;     && cClearUniqueID
            "0", ;                                           && cOptimizeByFilestamp (peligroso con ramas)
            loSection.get_value("cfgFile", "") ;             && cCFG_File
        )

        lnElapsed = INT((SECONDS() - lnStart) * 1000)

        DIMENSION laProcs[1, 6]
        lnCnt = 0
        TRY
            lnCnt = loFB.get_Processed(@laProcs, "*")
        CATCH
            lnCnt = 0
        ENDTRY

        FOR lnJ = 1 TO lnCnt
            emit_event(lcEventFile, ;
                '{"event":"file_processed"' + ;
                ',"opId":"' + json_esc(lcOpId) + '"' + ;
                ',"file":"' + json_esc(nvs(laProcs[lnJ, 1])) + '"' + ;
                ',"inOut":"' + json_esc(nvs(laProcs[lnJ, 2])) + '"' + ;
                ',"processed":' + json_bool(nvs(laProcs[lnJ, 3])) + ;
                ',"hasErrors":' + json_bool(nvs(laProcs[lnJ, 4])) + ;
                ',"supported":' + json_bool(nvs(laProcs[lnJ, 5])) + ;
                ',"expanded":' + json_bool(nvs(laProcs[lnJ, 6])) + '}')
        ENDFOR

        emit_event(lcEventFile, ;
            '{"event":"op_done"' + ;
            ',"opId":"' + json_esc(lcOpId) + '"' + ;
            ',"returnCode":' + TRANSFORM(lnRet) + ;
            ',"elapsedMs":' + TRANSFORM(lnElapsed) + '}')

        IF lnRet == 0
            lnOkCount = lnOkCount + 1
        ELSE
            lnErrCount = lnErrCount + 1
        ENDIF

    CATCH TO loEx
        lnElapsed = INT((SECONDS() - lnStart) * 1000)
        emit_event(lcEventFile, ;
            '{"event":"op_error"' + ;
            ',"opId":"' + json_esc(lcOpId) + '"' + ;
            ',"errorNo":' + TRANSFORM(loEx.ErrorNo) + ;
            ',"message":"' + json_esc(loEx.Message) + '"' + ;
            ',"lineNo":' + TRANSFORM(loEx.LineNo) + ;
            ',"lineContents":"' + json_esc(nvs(loEx.LineContents)) + '"' + ;
            ',"details":"' + json_esc(nvs(loEx.Details)) + '"' + ;
            ',"elapsedMs":' + TRANSFORM(lnElapsed) + '}')
        lnErrCount = lnErrCount + 1
    ENDTRY

    IF FILE(ADDBS(JUSTPATH(lcEventFile)) + ".cancel")
        emit_event(lcEventFile, ;
            '{"event":"cancelled","opsProcessed":' + TRANSFORM(lnI) + '}')
        EXIT
    ENDIF
ENDFOR

emit_event(lcEventFile, ;
    '{"event":"job_done"' + ;
    ',"okCount":' + TRANSFORM(lnOkCount) + ;
    ',"errCount":' + TRANSFORM(lnErrCount) + ;
    ',"elapsedMs":' + TRANSFORM(INT((SECONDS() - lnGlobalStart) * 1000)) + '}')

loFB = NULL
QUIT


*========================================================================
* Helpers de emision
*========================================================================
PROCEDURE emit_event
    LPARAMETERS tcFile, tcJson
    STRTOFILE(tcJson + CHR(13) + CHR(10), tcFile, 1)
ENDPROC

PROCEDURE emit_driver_error
    LPARAMETERS tcFile, tcMessage, tcStage
    emit_event(tcFile, ;
        '{"event":"driver_error"' + ;
        ',"message":"' + json_esc(tcMessage) + '"' + ;
        ',"stage":"' + json_esc(tcStage) + '"}')
ENDPROC


*========================================================================
* Utilidades
*========================================================================
FUNCTION nvs
    * NVL -> string; convierte null a "" y no-string a TRANSFORM
    LPARAMETERS tv
    IF ISNULL(tv)
        RETURN ""
    ENDIF
    IF VARTYPE(tv) == "C"
        RETURN tv
    ENDIF
    RETURN TRANSFORM(tv)
ENDFUNC

FUNCTION json_bool
    * get_Processed() devuelve los flags como tokens: "P1"/"P0", "E1"/"E0",
    * "S1"/"S0", "X1"/"X0". Basta el ultimo caracter para saber el bit.
    LPARAMETERS tv
    LOCAL lc
    lc = ALLTRIM(nvs(tv))
    IF EMPTY(lc)
        RETURN "0"
    ENDIF
    RETURN IIF(RIGHT(lc, 1) == "1", "1", "0")
ENDFUNC

FUNCTION json_esc
    LPARAMETERS tc
    LOCAL lcR, lnI, lnC, lcAcum
    IF ISNULL(tc)
        RETURN ""
    ENDIF
    tc = nvs(tc)
    lcR = ""
    lcAcum = ""
    FOR lnI = 1 TO LEN(tc)
        lnC = ASC(SUBSTR(tc, lnI, 1))
        DO CASE
        CASE lnC == 34
            lcR = lcR + lcAcum + '\"'
            lcAcum = ""
        CASE lnC == 92
            lcR = lcR + lcAcum + '\\'
            lcAcum = ""
        CASE lnC == 8
            lcR = lcR + lcAcum + '\b'
            lcAcum = ""
        CASE lnC == 9
            lcR = lcR + lcAcum + '\t'
            lcAcum = ""
        CASE lnC == 10
            lcR = lcR + lcAcum + '\n'
            lcAcum = ""
        CASE lnC == 12
            lcR = lcR + lcAcum + '\f'
            lcAcum = ""
        CASE lnC == 13
            lcR = lcR + lcAcum + '\r'
            lcAcum = ""
        CASE lnC < 32 OR lnC > 126
            lcR = lcR + lcAcum + '\u' + PADL(dec2hex(lnC), 4, "0")
            lcAcum = ""
        OTHERWISE
            lcAcum = lcAcum + CHR(lnC)
        ENDCASE
    ENDFOR
    RETURN lcR + lcAcum
ENDFUNC

FUNCTION dec2hex
    LPARAMETERS tnN
    LOCAL lcH, lnR
    tnN = INT(tnN)
    IF tnN == 0
        RETURN "0"
    ENDIF
    lcH = ""
    DO WHILE tnN > 0
        lnR = MOD(tnN, 16)
        lcH = SUBSTR("0123456789ABCDEF", lnR + 1, 1) + lcH
        tnN = INT(tnN / 16)
    ENDDO
    RETURN lcH
ENDFUNC

FUNCTION iso_now
    LOCAL lt, lcD
    lt = DATETIME()
    lcD = DTOS(TTOD(lt))
    RETURN LEFT(lcD, 4) + "-" + SUBSTR(lcD, 5, 2) + "-" + SUBSTR(lcD, 7, 2) + ;
        "T" + PADL(TRANSFORM(HOUR(lt)), 2, "0") + ":" + ;
        PADL(TRANSFORM(MINUTE(lt)), 2, "0") + ":" + ;
        PADL(TRANSFORM(SEC(lt)), 2, "0")
ENDFUNC

FUNCTION detect_fb2p_version
    * Extrae el numero de version del header de foxbin2prg.pj2, que se ve asi:
    *   *< FOXBIN2PRG: Version="1.21" SourceFile="foxbin2prg.pjx" CPID="1252" />
    LPARAMETERS tcHome
    LOCAL lcHeader, lcPj2, lnStart, lnEnd, lcAfter, lcResult
    lcResult = ""
    lcPj2 = ADDBS(nvs(tcHome)) + "foxbin2prg.pj2"
    IF NOT FILE(lcPj2)
        RETURN ""
    ENDIF
    TRY
        lcHeader = FILETOSTR(lcPj2)
        IF LEN(lcHeader) > 2048
            lcHeader = LEFT(lcHeader, 2048)
        ENDIF
        lnStart = ATC('Version="', lcHeader)
        IF lnStart > 0
            lnStart = lnStart + LEN('Version="')
            lcAfter = SUBSTR(lcHeader, lnStart)
            lnEnd = AT('"', lcAfter)
            IF lnEnd > 1
                lcResult = ALLTRIM(LEFT(lcAfter, lnEnd - 1))
            ENDIF
        ENDIF
    CATCH
        lcResult = ""
    ENDTRY
    RETURN lcResult
ENDFUNC

FUNCTION sanitize_ctype
    * Normaliza el cType removiendo INTERACTIVE (bloquea con dialogo) y
    * SHOWMSG (bloquea con MessageBox al finalizar).
    *
    * Modo proyecto: FoxBin2Prg entra al modo 'todo el proyecto' cuando el
    * cType EMPIEZA con '*' y el archivo es un .PJX/.PJ2 (la direccion la
    * decide la extension). '*' incluye el propio archivo de proyecto,
    * '*-' lo excluye. Se devuelve el prefijo tal cual y se sale temprano:
    * el recorte de guiones de mas abajo convertiria '*-' en '*', que es
    * exactamente lo contrario de lo pedido.
    LPARAMETERS tc
    LOCAL lc
    lc = UPPER(ALLTRIM(nvs(tc)))
    IF LEFT(lc, 1) == '*'
        RETURN IIF(LEFT(lc, 2) == '*-', '*-', '*')
    ENDIF
    lc = STRTRAN(lc, "INTERACTIVE", "")
    lc = STRTRAN(lc, "SHOWMSG", "")
    DO WHILE "--" $ lc
        lc = STRTRAN(lc, "--", "-")
    ENDDO
    IF LEFT(lc, 1) == "-"
        lc = SUBSTR(lc, 2)
    ENDIF
    IF RIGHT(lc, 1) == "-"
        lc = LEFT(lc, LEN(lc) - 1)
    ENDIF
    RETURN lc
ENDFUNC


*========================================================================
* Parser INI minimo (lo que necesitamos, nada mas)
*========================================================================
FUNCTION parse_ini
    LPARAMETERS tcContent
    LOCAL loRoot, loSection, lcLine, lcSecName, lcKey, lcVal
    LOCAL lnCnt, lnI, lnEq
    LOCAL ARRAY laLines[1]

    loRoot = CREATEOBJECT("ini_root")
    loSection = NULL
    lnCnt = ALINES(laLines, tcContent, 1 + 4)    && 1=trim, 4=skip empty

    FOR lnI = 1 TO lnCnt
        lcLine = ALLTRIM(laLines[lnI])
        IF EMPTY(lcLine) OR LEFT(lcLine, 1) == ";" OR LEFT(lcLine, 1) == "#"
            LOOP
        ENDIF
        IF LEFT(lcLine, 1) == "[" AND RIGHT(lcLine, 1) == "]"
            lcSecName = LOWER(ALLTRIM(SUBSTR(lcLine, 2, LEN(lcLine) - 2)))
            loSection = CREATEOBJECT("ini_section")
            loSection.sec_name = lcSecName
            IF LEFT(lcSecName, 3) == "op:"
                loSection.op_id = SUBSTR(lcSecName, 4)
                loRoot.op_count = loRoot.op_count + 1
            ENDIF
            loRoot.sections.Add(loSection, lcSecName)
            LOOP
        ENDIF
        IF ISNULL(loSection)
            LOOP
        ENDIF
        lnEq = AT("=", lcLine)
        IF lnEq == 0
            LOOP
        ENDIF
        lcKey = LOWER(ALLTRIM(LEFT(lcLine, lnEq - 1)))
        lcVal = ALLTRIM(SUBSTR(lcLine, lnEq + 1))
        loSection.values.Add(lcVal, lcKey)
    ENDFOR

    RETURN loRoot
ENDFUNC

FUNCTION get_val
    LPARAMETERS toRoot, tcSection, tcKey, tcDefault
    LOCAL loSec, lcDefault
    lcDefault = IIF(PCOUNT() >= 4, tcDefault, "")
    loSec = toRoot.section_by_name(tcSection)
    IF ISNULL(loSec)
        RETURN lcDefault
    ENDIF
    RETURN loSec.get_value(tcKey, lcDefault)
ENDFUNC


DEFINE CLASS ini_root AS Custom
    op_count = 0
    sections = NULL

    PROCEDURE Init
        THIS.sections = CREATEOBJECT("Collection")
    ENDPROC

    FUNCTION section_by_name
        LPARAMETERS tcName
        LOCAL loS, lnI, lcT
        lcT = LOWER(ALLTRIM(tcName))
        FOR lnI = 1 TO THIS.sections.Count
            loS = THIS.sections.Item(lnI)
            IF loS.sec_name == lcT
                RETURN loS
            ENDIF
        ENDFOR
        RETURN NULL
    ENDFUNC

    FUNCTION op_at
        LPARAMETERS tnIdx
        LOCAL loS, lnI, lnN
        lnN = 0
        FOR lnI = 1 TO THIS.sections.Count
            loS = THIS.sections.Item(lnI)
            IF LEFT(loS.sec_name, 3) == "op:"
                lnN = lnN + 1
                IF lnN == tnIdx
                    RETURN loS
                ENDIF
            ENDIF
        ENDFOR
        RETURN NULL
    ENDFUNC
ENDDEFINE


DEFINE CLASS ini_section AS Custom
    sec_name = ""
    op_id = ""
    values = NULL

    PROCEDURE Init
        THIS.values = CREATEOBJECT("Collection")
    ENDPROC

    FUNCTION get_value
        LPARAMETERS tcKey, tcDefault
        LOCAL lcKey, lcResult, lcDefault
        lcDefault = IIF(PCOUNT() >= 2, tcDefault, "")
        lcKey = LOWER(ALLTRIM(tcKey))
        lcResult = lcDefault
        TRY
            lcResult = THIS.values.Item(lcKey)
        CATCH
            lcResult = lcDefault
        ENDTRY
        RETURN lcResult
    ENDFUNC
ENDDEFINE
