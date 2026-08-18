CREATE TABLE IF NOT EXISTS oportunidades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT now(),

    origem_cidade TEXT NOT NULL,
    origem_uf CHAR(2) NOT NULL,
    destino_cidade TEXT NOT NULL,
    destino_uf CHAR(2) NOT NULL,
    mercadoria TEXT,
    peso_kg NUMERIC,
    cubagem_m3 NUMERIC,
    valor_nf NUMERIC,
    veiculo_pedido TEXT,
    carroceria TEXT,
    empresa TEXT,
    contato TEXT,
    observacoes TEXT,
    fonte TEXT DEFAULT 'cargas.com.br',
    data_anuncio TIMESTAMPTZ,

    distancia_km NUMERIC,
    tempo_viagem_min INTEGER,
    confianca TEXT CHECK (confianca IN ('ALTA','MEDIA','BAIXA')),

    elegibilidade TEXT CHECK (elegibilidade IN ('APROVADA','RECUSADA','BLOQUEIO','REVISAR')),
    motivo_elegibilidade TEXT,
    faixa_gr CHAR(1),
    classificacao_mercadoria TEXT CHECK (classificacao_mercadoria IN ('EXCLUIDA','ESPECIFICA','NAO_ESPECIFICA','REVISAR')),

    modalidade TEXT CHECK (modalidade IN ('DEDICADO','FRACIONADO')),

    veiculo_sugerido TEXT,
    eixos INTEGER,
    fracao_ocupacao NUMERIC,
    restricao_dominante TEXT,
    custo_total NUMERIC,
    preco_minimo NUMERIC,
    preco_alvo NUMERIC,
    preco_maximo NUMERIC,

    score NUMERIC,
    status TEXT DEFAULT 'CAPTADA' CHECK (status IN (
        'CAPTADA','INCOMPLETA','RECUSADA','CALCULADA','CONTATADA',
        'PROPOSTA_ENVIADA','EM_NEGOCIACAO','FECHADA','PERDIDA','CANCELADA'
    )),
    preco_enviado NUMERIC,
    preco_final NUMERIC,
    custo_real NUMERIC,
    motivo_perda TEXT,
    num_rodadas INTEGER DEFAULT 0,
    num_followups INTEGER DEFAULT 0,
    cliente_recorrente BOOLEAN DEFAULT FALSE,
    averbada BOOLEAN DEFAULT FALSE,

    data_primeiro_contato TIMESTAMPTZ,
    data_proposta TIMESTAMPTZ,
    data_fechamento TIMESTAMPTZ,

    hash_dedup TEXT,
    UNIQUE(hash_dedup)
);

CREATE INDEX IF NOT EXISTS idx_oport_status ON oportunidades(status);
CREATE INDEX IF NOT EXISTS idx_oport_score ON oportunidades(score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_oport_created ON oportunidades(created_at DESC);

CREATE TABLE IF NOT EXISTS followups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    oportunidade_id UUID REFERENCES oportunidades(id),
    tipo TEXT NOT NULL,
    data_prevista DATE NOT NULL,
    data_executada DATE,
    conteudo_rascunho TEXT,
    status TEXT DEFAULT 'PENDENTE' CHECK (status IN ('PENDENTE','ENVIADO','CANCELADO'))
);

CREATE INDEX IF NOT EXISTS idx_followup_pendente ON followups(data_prevista) WHERE status = 'PENDENTE';
