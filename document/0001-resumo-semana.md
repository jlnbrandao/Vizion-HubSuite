*Lanstar — resumo da semana*

*Período de trabalho*: 4 dias de serviço, distribuídos da seguinte forma:
• Segunda-feira: dia todo
• Terça-feira: dia todo
• Quarta-feira: somente pela manhã
• Quinta-feira: somente pela manhã
• Sexta-feira: dia todo

Subi o projeto do zero: template de autenticação e permissões (RBAC) com backend FastAPI + frontend Vue/Quasar.

O que ficou pronto:
• Instalação do Docker e Docker Compose
• Instalação do PostgreSQL e Redis
• Login com JWT (usuário/senha)
• CRUD de usuários, roles e permissões
• Dashboard por perfil (admin, manager, operator, client, viewer)
• Login por username (não só e-mail)
• Layout novo (menu, header, páginas por perfil) + mapa na tela principal do client
• Deploy no servidor (nginx + systemd)
• Seed de dados demo

*Acesso*
http://134.209.122.250

*Contas para testar* (senha igual em todas: 123Mudar.)

1) Usuário: galileu
   Perfil: ADMIN (administração)

2) Usuário: manager
   Perfil: MANAGER (gestor)

3) Usuário: operator
   Perfil: OPERATOR (operador)

4) Usuário: user
   Perfil: CLIENT (cliente)

5) Usuário: viewer
   Perfil: VIEWER (somente leitura)
