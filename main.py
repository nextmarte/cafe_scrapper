import os
import csv
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import random

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)


def configurar_navegador():
    """Configura e retorna uma instância do navegador Chrome"""
    # Opções do Chrome
    options = Options()

    # Habilitar modo headless - navegador fica invisível
    # Nova sintaxe para headless em versões recentes do Chrome
    options.add_argument("--headless=new")

    # Configurações adicionais necessárias para o modo headless
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument("--disable-extensions")
    # Importante para headless em Windows
    options.add_argument("--disable-gpu")
    # Importante para execução sem problemas
    options.add_argument("--no-sandbox")
    # Evita problemas em ambientes com pouca memória
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    # User agent
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        # Instalar e usar o ChromeDriver automaticamente
        driver = webdriver.Chrome(service=Service(
            ChromeDriverManager().install()), options=options)

        # Modificar o navigator.webdriver para evitar detecção de automação
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        logging.info("Navegador iniciado em modo headless (invisível)")
        return driver
    except Exception as e:
        logging.error(f"Erro ao configurar o navegador: {e}")
        print(f"Erro ao configurar o navegador: {e}")
        print("Verifique se o Chrome está instalado e tente novamente.")
        return None


def extrair_dados_cafe(url):
    """Extrai informações sobre cafés do site da Nescafé Dolce Gusto usando Selenium"""
    driver = configurar_navegador()
    if not driver:
        return []

    resultados = []

    # Determinar a categoria com base na URL
    if "cafes" in url:
        categoria = "Café"
    elif "cappuccino-latte" in url:
        categoria = "Cappuccino/Latte"
    elif "chocolate" in url:
        categoria = "Chocolate"
    else:
        categoria = "Outros"

    try:
        # Acessar a página
        logging.info(f"Acessando a página: {url}")
        driver.get(url)

        # Espera inicial para a página carregar completamente
        time.sleep(5)  # Aumentado para 5 segundos

        # Aceitar cookies se aparecer (muitos sites exibem banners de cookies)
        try:
            botao_cookies = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.cookie-notice-accept-button, button.agree-button, button.consent-accept"))
            )
            botao_cookies.click()
            logging.info("Banner de cookies aceito")
            time.sleep(2)
        except:
            logging.info(
                "Nenhum banner de cookies encontrado ou não foi necessário aceitar")

        # Tentar diferentes seletores para encontrar os produtos
        logging.info("Tentando localizar os produtos na página...")

        # Verificar se há produtos na página usando diferentes seletores
        seletores_produto = [
            "li.product-item",
            "div.product-item-info",
            ".products-grid .item",
            "div.product-card",
            "div.product-item-details"
        ]

        produtos = []
        for seletor in seletores_produto:
            try:
                # Esperar explicitamente pelo seletor
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, seletor))
                )
                # Se chegar aqui, encontrou elementos com este seletor
                produtos = driver.find_elements(By.CSS_SELECTOR, seletor)
                logging.info(
                    f"Encontrados {len(produtos)} produtos usando o seletor: {seletor}")
                if produtos:
                    break  # Encontrou produtos, sai do loop
            except:
                continue  # Tenta o próximo seletor

        # Se ainda não encontramos produtos, vamos tentar uma abordagem diferente
        if not produtos:
            logging.warning(
                "Nenhum produto encontrado pelos seletores comuns. Tentando capturar a estrutura HTML...")

            # Salvar o HTML da página para depuração
            html_file = f"pagina_{categoria.lower().replace('/', '_')}.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            logging.info(
                f"HTML da página salvo em {html_file} para análise manual")

            # Tenta encontrar qualquer elemento que possa conter informações de produto
            produtos = driver.find_elements(
                By.CSS_SELECTOR, "a.product-card__name--link, h2.product-name, div.product-card")

        # Extrair dados de cada produto encontrado
        for produto in produtos:
            try:
                # Extrair texto do elemento para ver o que contém
                conteudo = produto.text
                # Mostra os primeiros 100 caracteres
                logging.info(f"Conteúdo encontrado: {conteudo[:100]}...")

                # Tenta encontrar as informações do produto com diferentes abordagens
                nome = "Nome não disponível"
                preco = "Preço não disponível"
                imagem_url = "Imagem não disponível"
                descricao = "Descrição não disponível"
                intensidade = "Não informado"
                disponibilidade = "Status desconhecido"
                link_produto = ""

                # Nome do café e link do produto (várias tentativas)
                nome_elementos = produto.find_elements(By.CSS_SELECTOR,
                                                       "a.product-card__name--link, h2.product-name a, div.product-name, span.product-item-name")
                if nome_elementos:
                    nome = nome_elementos[0].text.strip()
                    # Capturar o link do produto
                    link_produto = nome_elementos[0].get_attribute(
                        "href") or ""

                # Se não conseguiu o nome pelo texto, tenta pelo atributo alt da imagem
                if nome == "Nome não disponível":
                    img_elementos = produto.find_elements(
                        By.CSS_SELECTOR, "img")
                    if img_elementos:
                        nome = img_elementos[0].get_attribute(
                            "alt") or "Nome não disponível"

                # URL da imagem (várias tentativas)
                img_elementos = produto.find_elements(By.CSS_SELECTOR,
                                                      "img.product-image, img.photo, div.product-image-container img")
                if img_elementos:
                    imagem_url = img_elementos[0].get_attribute(
                        "src") or img_elementos[0].get_attribute("data-src") or "Imagem não disponível"

                # Preço (várias tentativas)
                preco_elementos = produto.find_elements(By.CSS_SELECTOR,
                                                        "span.price, div.price-box .price, span.normal-price .price")
                if preco_elementos:
                    preco = preco_elementos[0].text.strip()

                # Descrição curta - Novo seletor para "Equilibrado e Intenso", etc.
                descricao_elementos = produto.find_elements(By.CSS_SELECTOR,
                                                            "div.product-card__description--short, div.product-card__short-description")
                if descricao_elementos:
                    descricao = descricao_elementos[0].text.strip()
                    if not descricao:  # Se estiver vazio, tente obter pelo innerHTML
                        descricao = descricao_elementos[0].get_attribute(
                            "innerHTML").strip()

                # Limpar a descrição de possíveis HTML tags ou espaços extras
                if descricao != "Descrição não disponível":
                    # Remover múltiplos espaços e quebras de linha
                    import re
                    descricao = re.sub(r'\s+', ' ', descricao).strip()

                # Verificar disponibilidade em estoque
                # Primeiro, verificar se tem a mensagem de "Sem Estoque"
                sem_estoque_elementos = produto.find_elements(By.CSS_SELECTOR,
                                                              "span.product-card__stock-availability--oos, .out-of-stock")

                if sem_estoque_elementos and any("sem estoque" in e.text.lower() for e in sem_estoque_elementos):
                    disponibilidade = "Sem Estoque"
                else:
                    # Verificar se tem botão de adicionar ao carrinho
                    add_to_cart = produto.find_elements(
                        By.CSS_SELECTOR, "button.tocart, button.action.tocart.primary")
                    disponibilidade = "Em Estoque" if add_to_cart else "Sem Estoque"

                # Adicionar à lista de resultados se pelo menos temos um nome ou preço válido
                if nome != "Nome não disponível" or preco != "Preço não disponível":
                    cafe_info = {
                        'categoria': categoria,
                        'nome': nome,
                        'preco': preco,
                        'descricao': descricao,
                        'intensidade': intensidade,
                        'disponibilidade': disponibilidade,
                        'imagem_url': imagem_url,
                        'link_produto': link_produto
                    }

                    resultados.append(cafe_info)
                    logging.info(
                        f"Produto encontrado: {nome} - {preco} - {disponibilidade} - Desc: '{descricao}' - Categoria: {categoria}")

            except Exception as e:
                logging.error(f"Erro ao processar elemento: {str(e)}")

        # Se não encontramos produtos, tentar fazer um screenshot para análise
        if not resultados:
            screenshot_path = f"pagina_{categoria.lower().replace('/', '_')}_screenshot.png"
            driver.save_screenshot(screenshot_path)
            logging.info(
                f"Screenshot salvo em {screenshot_path} para análise manual")

    except Exception as e:
        logging.error(f"Erro durante a extração: {str(e)}")

    finally:
        # Fechar o navegador
        logging.info("Fechando o navegador...")
        driver.quit()

    return resultados


def extrair_dados_multiplas_categorias(urls):
    """Extrai dados de várias categorias e retorna todos os resultados"""
    todos_resultados = []

    for url in urls:
        logging.info(f"Iniciando extração para URL: {url}")
        resultados = extrair_dados_cafe(url)
        logging.info(f"Extraídos {len(resultados)} produtos da URL: {url}")
        todos_resultados.extend(resultados)

        # Pequena pausa entre categorias
        time.sleep(random.uniform(5, 10))

    return todos_resultados


def salvar_csv(resultados, nome_arquivo="produtos_nescafe.csv"):
    """Salva os resultados em um arquivo CSV"""
    if not resultados:
        logging.error("Sem dados para salvar no CSV!")
        return False

    try:
        with open(nome_arquivo, 'w', newline='', encoding='utf-8') as arquivo:
            campos = ['categoria', 'nome', 'preco', 'descricao',
                      'intensidade', 'disponibilidade', 'imagem_url', 'link_produto']
            writer = csv.DictWriter(arquivo, fieldnames=campos)

            writer.writeheader()
            writer.writerows(resultados)

        tamanho_arquivo = os.path.getsize(nome_arquivo)
        logging.info(
            f"Dados salvos em {nome_arquivo} ({tamanho_arquivo} bytes)")
        return True

    except Exception as e:
        logging.error(f"Erro ao salvar CSV: {e}")
        return False


def main():
    """Função principal"""
    print("Iniciando extração de dados de produtos da Nescafé Dolce Gusto...")
    print("Este script usa o Selenium para controlar um navegador Chrome em modo headless (invisível).")

    # Lista de URLs para extrair
    urls = [
        "https://www.nescafe-dolcegusto.com.br/sabores/cafes",
        "https://www.nescafe-dolcegusto.com.br/sabores/cappuccino-latte",
        "https://www.nescafe-dolcegusto.com.br/sabores/chocolate"
    ]

    print(f"Serão extraídas informações de {len(urls)} categorias diferentes.")

    # Extrair dados de todas as categorias
    resultados = extrair_dados_multiplas_categorias(urls)

    if resultados:
        print(
            f"Extração concluída! Encontrados {len(resultados)} produtos no total.")

        # Resumo por categoria
        categorias = {}
        for item in resultados:
            cat = item['categoria']
            if cat in categorias:
                categorias[cat] += 1
            else:
                categorias[cat] = 1

        print("\nResumo por categoria:")
        for cat, qtd in categorias.items():
            print(f"- {cat}: {qtd} produtos")

        nome_arquivo = "produtos_nescafe.csv"
        if salvar_csv(resultados, nome_arquivo):
            print(f"Os dados foram salvos em: {os.path.abspath(nome_arquivo)}")
            print("Você pode abrir este arquivo no Excel ou outro programa de planilhas.")
        else:
            print("Erro ao salvar os dados em CSV.")
    else:
        print("Não foi possível extrair dados. Verifique o log para mais detalhes.")
        print("Foram salvos arquivos HTML e screenshots para análise manual.")


if __name__ == "__main__":
    main()
