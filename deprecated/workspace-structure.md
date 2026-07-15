so instead treating dpu as its own unit, it should realy just be split between external experiment pyscripts ran by the user, interal pyscripts to the evolver server for systems management, then an external data visibility tools like the /home/ash/Documents/work/evolver_code/dpu/graphing

tho those mamangert scripts should still not be part of the evolver server proc, since they are oneshots taht may need to be interupted

realy we need to reaproach the organization of this whole codebase in the context that the evolver server runs on a computer, likely the same computer that will be dispatching dpu scripts and jobs like calibration, especialy given the context that we will be setting this up as dedicated console like units to simplify ussage for those less familair with the command line and intermachine connectivity
realy we need a super unit to manage all of these other py procs which kicks out to a data visibility layer ( which should in the future be packaged into a ui that allows simpler control)

we could turn dpu into a true command like tool

1. i want the evolver server to be its own unit, since its continuity is the most important,
    - it is responsible for  evolver_machine_lifetime_management
        - so owns the scripts for firmware_flashing, identity_management
        - is supplied the firmware (or pointed to file containing)
        - already owns interactin with the evolver machines, and reading signals
    - is not trusted to flash and recalibate evolver machines on its own
        - so needs a way to ask for permision
were turning it into an integrated system with simplified user facing components
2. control proc 
    - control proc will be responsible for the whole integrated setup
        - evolver server management
            - monitor
            - start/restart
        - computer management
        - data flow
            - expose to ui
            - sync to catalogue
            - ingest from evolver-server stream, assemble into expirmental data
    - effectivly spawns/runs dpu scripts
        - if it spawns, then the evolver-server stream would be routed to the dpu threat, and the results sent back
        - if it runs, if a script is bad could cause it to crash, but 
    - so manages experiment lifetime
        - if its constantly injesting data from the evolvers, would need to know what to put into docs and what to put into 
    - proclaim formats for intersystem actions
3. ui
    - will be an seperate overlay over the control proc
        - sends user requests and asks for data out
    - can take form of webui, tui, or local app ui
        - use modular approach, where they will be a client to the control proc
        - control proc exposes data, ui sends user commands
    - functions
        - observation
            - live data
            - graphs
            - historical data
        - experiment configuration
            - user fills forms
            - config data export ( usb, data_catalog, etc)
            - name experiment
        - admin
            - submit scripts
            - build forms
            - metadat format
        - user sends commands through ui actions
            - start expirament job
            - interupt live experiment
            - pause experiment
            - resume experiment
                - from break or pause
        - authorize risky evolver-server actions
            - flashing
            - calibrations
        - guide user
            - present guides and helpfull advice at relavent pages in the ui
4. data store
    - local
        - this is where we will locate all of the local data
        - includes from live state
        - lifetime
            - machine data, admin only
                - identity
                - calibrations
                - logs
            - state
                - this would be the historical machine state data, expose to admins, would allow us to track, diagnose, fix
            - 1 dataset per machine or cluster
        - session
            - one dataset per expirament
            - experiment data
            - experiment config
            - errors/logs
        - user/customer
            - one dataset per user
            - user data
            - user templates
        - config
            - templates
            - firmware
            - data formats
    - remote
        - need to decide how much to mirror 
        - data catalog
            - lifetime
                - 1 dataset per machine or cluster
                - access: admin
            - session
                - one dataset per expirament
                - access: user
            - user/customer
                - one dataset per user
                - access: user
            - config
                - prob one coredataset
                - admin location to distribuite config, templates, formats, forms







need to seperate data_coalation and management from dpu

