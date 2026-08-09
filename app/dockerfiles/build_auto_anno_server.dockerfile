FROM lkdi/auto-anno-server:2.0.0

LABEL Will, Cheng Yong <chengy@luokung.com>

WORKDIR /app

COPY auto_anno_entrypoint.sh /run/entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["bash", "/run/entrypoint.sh"]