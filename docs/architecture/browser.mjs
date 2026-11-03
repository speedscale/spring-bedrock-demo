import mermaid from 'mermaid';

window.drawArchitecture = async (source, packs) => {
  mermaid.registerIconPacks(packs.map(pack => ({name: pack.prefix, icons: pack})));
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: 'strict',
    htmlLabels: false,
    theme: 'base',
    look: 'classic',
    themeCSS: '.cluster-label text {font-size:18px!important;font-weight:600;}',
    markdownAutoWrap: false,
    fontFamily: 'Arial, Helvetica, sans-serif',
    themeVariables: {
      primaryColor: '#F4F8FF', primaryTextColor: '#182B43',
      primaryBorderColor: '#9DB9E0', lineColor: '#2864D8',
      secondaryColor: '#E8F5F0', tertiaryColor: '#FFFFFF',
      fontSize: '22px', background: '#FFFFFF'
    },
    layout: 'dagre',
    flowchart: { wrappingWidth: 400, nodeSpacing: 55, rankSpacing: 40, padding: 18, subGraphTitleMargin: {top: 0, bottom: 0}, curve: 'linear'}
  });
  const {svg} = await mermaid.render('architectureDiagram', source);
  document.querySelector('#diagram').innerHTML = svg;
  await document.fonts.ready;
  return new XMLSerializer().serializeToString(document.querySelector('#diagram > svg'));
};
