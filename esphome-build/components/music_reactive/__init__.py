import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

DEPENDENCIES = ['fastcon']

MusicReactiveEffectUDP = cg.global_ns.class_('MusicReactiveEffectUDP', cg.Component)

CONF_FASTCON_ID = "fastcon_id"

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(MusicReactiveEffectUDP),
    cv.Required(CONF_FASTCON_ID): cv.use_id(cg.esphome_ns.namespace('fastcon').class_('FastconController')),
}).extend(cv.COMPONENT_SCHEMA)

async def to_code(config):
    cg.add_library("arduinoFFT", "^1.9")
    cg.add(cg.RawExpression('#include "music_reactive.h"'))
    
    var = cg.new_Pvariable(config[CONF_ID], True) # True for master mode
    await cg.register_component(var, config)
    
    fastcon = await cg.get_variable(config[CONF_FASTCON_ID])
    cg.add(var.set_controller(fastcon))
