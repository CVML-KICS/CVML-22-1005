# lightning imports
from pytorch_lightning import LightningModule, LightningDataModule, Callback, Trainer
from pytorch_lightning.loggers import LightningLoggerBase
from pytorch_lightning import seed_everything

# hydra imports
from omegaconf import DictConfig
from hydra.utils import log
import hydra

# normal imports
from typing import List

# src imports
from src.utils import template_utils as utils


def train(config: DictConfig):

    # A couple of optional utilities:
    # - disabling warnings
    # - disabling lightning logs
    # - easier access to debug mode
    # - forcing debug friendly configuration
    # You can safely get rid of this line if you don't want those
    utils.extras(config)

    # Pretty print config using Rich library
    if config.get("print_config"):
        log.info(f"Pretty printing config with Rich! <{config.print_config}>")
        utils.print_config(config, resolve=True)

    # Set seed for random number generators in pytorch, numpy and python.random
    if "seed" in config:
        seed_everything(config.seed)

    # Init Lightning datamodule ⚡
    log.info(f"Instantiating datamodule <{config.datamodule._target_}>")
    datamodule: LightningDataModule = hydra.utils.instantiate(config.datamodule)

    # Init Lightning model ⚡
    log.info(f"Instantiating model <{config.model._target_}>")
    model: LightningModule = hydra.utils.instantiate(
        config.model, optimizer=config.optimizer, _recursive_=False
    )

    # Init Lightning callbacks ⚡
    callbacks: List[Callback] = []
    if "callbacks" in config:
        for _, cb_conf in config["callbacks"].items():
            if "_target_" in cb_conf:
                log.info(f"Instantiating callback <{cb_conf._target_}>")
                callbacks.append(hydra.utils.instantiate(cb_conf))

    # Init Lightning loggers ⚡
    logger: List[LightningLoggerBase] = []
    if "logger" in config:
        for _, lg_conf in config["logger"].items():
            if "_target_" in lg_conf:
                log.info(f"Instantiating logger <{lg_conf._target_}>")
                logger.append(hydra.utils.instantiate(lg_conf))

    # Init Lightning trainer ⚡
    log.info(f"Instantiating trainer <{config.trainer._target_}>")
    trainer: Trainer = hydra.utils.instantiate(
        config.trainer, callbacks=callbacks, logger=logger
    )

    # Send some parameters from config to all lightning loggers
    log.info(f"Logging hyperparameters!")
    utils.log_hyperparameters(
        config=config,
        model=model,
        datamodule=datamodule,
        trainer=trainer,
        callbacks=callbacks,
        logger=logger,
    )

    # Train the model ⚡
    log.info(f"Starting training!")
    trainer.fit(model=model, datamodule=datamodule)

    # Evaluate model on test set after training
    # if not config.trainer.get("fast_dev_run"):
    #     log.info(f"Starting testing!")
    #     trainer.test()

    # Make sure everything closed properly
    log.info(f"Finalizing!")
    utils.finish(
        config=config,
        model=model,
        datamodule=datamodule,
        trainer=trainer,
        callbacks=callbacks,
        logger=logger,
    )

    # Return metric score for Optuna optimization
    optimized_metric = config.get("optimized_metric")
    if optimized_metric:
        return trainer.callback_metrics[optimized_metric]


@hydra.main(config_path="configs/", config_name="config.yaml")
def main(config: DictConfig):
    return train(config)


if __name__ == "__main__":
    main()
