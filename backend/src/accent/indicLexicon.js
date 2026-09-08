/**
 * Small, extensible lexicon used in two places:
 *
 * 1. TTS (ssmlBuilder.js): words here get wrapped in SSML <sub alias="...">
 *    or a custom-lexicon phoneme entry so Azure/other engines don't
 *    mispronounce common Indian names, places and loanwords the way a
 *    generic US-English voice would.
 *
 * 2. Accent layer (accentPreprocessor.js): romanized regional-language
 *    function words are used ONLY to raise the confidence of an
 *    "accent/code-switch" badge shown in the UI — never to rewrite or
 *    translate the transcript.
 *
 * This is intentionally small and easy to extend. In production, back
 * this with a proper pronunciation dictionary (e.g. an ISLE/CMU-style
 * lexicon extended with Indic entries) instead of a hardcoded list.
 */

// word -> IPA-ish respelling hint consumed by ssmlBuilder's <phoneme> tags.
// Only added where a generic English TTS voice is known to mispronounce it.
export const PRONUNCIATION_HINTS = {
  bengaluru: 'b_e_ng_g_uh_l_oo_r_u',
  kolkata: 'k_oh_l_k_a_t_a',
  chennai: 'ch_e_n_ai',
  guwahati: 'g_u_w_a_h_a_t_i',
  thiruvananthapuram: 't_i_r_u_v_a_n_a_n_t_a_p_u_r_a_m',
  visakhapatnam: 'v_i_s_a_k_h_a_p_a_t_n_a_m',
  coimbatore: 'k_oy_m_b_a_t_oo_r',
  madurai: 'm_a_d_u_r_ai',
  tiruchirapalli: 't_i_r_u_ch_i_r_a_p_a_l_l_i',
};

// Romanized function/discourse words from major Indian languages that
// commonly appear inside otherwise-English sentences (code-switching).
// Presence of these is a *signal*, not a translation trigger.
export const CODE_SWITCH_MARKERS = {
  hindi: ['kya', 'hai', 'nahi', 'nahin', 'matlab', 'accha', 'bhai', 'yaar', 'thoda', 'kyunki', 'bilkul'],
  tamil: ['illai', 'enna', 'seri', 'romba', 'nalla', 'vera', 'appadi', 'epdi', 'aiyo'],
  telugu: ['ledu', 'enti', 'bagundi', 'chala', 'em', 'kadha'],
  kannada: ['illa', 'yenu', 'chennagide', 'swalpa', 'guru'],
  malayalam: ['illa', 'entha', 'sheri', 'aanu', 'pinne'],
  bengali: ['bhalo', 'ki', 'khub', 'accha', 'na'],
};
