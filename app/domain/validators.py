import re


def validar_cpf(cpf: str) -> bool:
    """Valida CPF usando algoritmo oficial dos dígitos verificadores."""
    cpf = re.sub(r"\D", "", cpf)

    if len(cpf) != 11:
        return False

    if cpf == cpf[0] * 11:
        return False

    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    if int(cpf[9]) != digito1:
        return False

    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    return int(cpf[10]) == digito2


def validar_cnpj(cnpj: str) -> bool:
    """Valida CNPJ usando algoritmo oficial dos dígitos verificadores."""
    cnpj = re.sub(r"\D", "", cnpj)

    if len(cnpj) != 14:
        return False

    if cnpj == cnpj[0] * 14:
        return False

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto = soma % 11
    digito1 = 0 if resto < 2 else 11 - resto

    if int(cnpj[12]) != digito1:
        return False

    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto = soma % 11
    digito2 = 0 if resto < 2 else 11 - resto

    return int(cnpj[13]) == digito2


def validar_cpf_cnpj(documento: str) -> bool:
    """Valida CPF ou CNPJ conforme o tamanho."""
    numeros = re.sub(r"\D", "", documento)
    if len(numeros) == 11:
        return validar_cpf(numeros)
    elif len(numeros) == 14:
        return validar_cnpj(numeros)
    return False


def formatar_cpf_cnpj(documento: str) -> str:
    """Remove formatação, mantendo apenas números."""
    return re.sub(r"\D", "", documento)


def validar_placa(placa: str) -> bool:
    """Valida placa brasileira nos formatos antigo (ABC-1234) e Mercosul (ABC1D23)."""
    placa = placa.upper().replace("-", "").strip()
    if re.match(r"^[A-Z]{3}\d{4}$", placa):
        return True
   
    if re.match(r"^[A-Z]{3}\d[A-Z]\d{2}$", placa):
        return True
    return False


def formatar_placa(placa: str) -> str:
    """Normaliza placa para maiúsculas sem hífen."""
    return placa.upper().replace("-", "").strip()
