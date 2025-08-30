from hist_service.cli.cli_dto import CLI_DTO

class CLICalculator:
    def __init__(self):
        pass

    def calculate_cli(self, n_losses: float, n_orders: float) -> CLI_DTO:
        if n_orders == 0:
            return CLI_DTO(value=0.0)
        
        dri: float = n_losses / n_orders
        return CLI_DTO(value=dri)